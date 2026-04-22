"""Comprehensive evaluation: metrics, calibration, SHAP, backtests, walk-forward CV, ablation."""
import pandas as pd
import numpy as np
import os
import sys
import h3
import xgboost as xgb
import shap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import (
    average_precision_score, log_loss, brier_score_loss,
    precision_recall_curve, precision_score, recall_score, f1_score,
)
from sklearn.calibration import calibration_curve
from scipy.special import expit

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ml.config import TRAIN_CUTOFF, TEST_START, RANDOM_SEED, LABEL_HORIZON_DAYS
from train_onset import ONSET_FEATURES
from train_continuation import CONT_FEATURES

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
MODEL_DIR = os.path.join(BASE_DIR, "models")

# ── Walk-forward CV folds (expanding window, 17-day gap) ──────
CV_FOLDS = [
    {"train_end": "2022-12-31", "test_start": "2023-01-17", "test_end": "2023-03-31", "name": "Q1-2023"},
    {"train_end": "2023-03-31", "test_start": "2023-04-17", "test_end": "2023-06-30", "name": "Q2-2023"},
    {"train_end": "2023-06-30", "test_start": "2023-07-17", "test_end": "2023-09-30", "name": "Q3-2023"},
    {"train_end": "2023-09-30", "test_start": "2023-10-17", "test_end": "2023-12-31", "name": "Q4-2023"},
    {"train_end": "2023-12-31", "test_start": "2024-01-17", "test_end": "2024-03-31", "name": "Q1-2024"},
    {"train_end": "2024-03-31", "test_start": "2024-04-17", "test_end": "2024-06-14", "name": "Q2-2024"},
]

# ── Feature ablation groups ───────────────────────────────────
ABLATION_GROUPS = {
    "spatial_r1": ["neighbor_danger_avg", "neighbor_fatal_sum",
                   "neighbor_gdelt_hostility_avg", "neighbor_firms_avg",
                   "neighbor_ntl_avg", "spatial_gradient"],
    "spatial_r2": ["neighbor_danger_r2"],
    "gdelt_base": [
        "gdelt_event_count", "gdelt_avg_tone", "gdelt_min_goldstein",
        "gdelt_avg_goldstein", "gdelt_num_articles", "gdelt_hostility",
    ],
    "gdelt_dynamics": [
        "gdelt_hostility_roll3d", "gdelt_hostility_roll7d", "gdelt_hostility_velocity",
        "gdelt_event_roll3d", "gdelt_event_roll7d", "gdelt_event_velocity",
        "gdelt_tone_delta",
    ],
    "ntl": ["ntl_mean", "ntl_delta_7d", "ntl_anomaly_30d"],
    "firms": ["firms_hotspot_count", "firms_avg_frp", "firms_max_frp",
              "firms_spike", "neighbor_firms_spike_sum"],
    "weather": ["temp_max", "temp_anomaly_30d", "precip_mm", "precip_spike"],
    "calendar": ["is_ramadan", "is_jerusalem_day", "is_election_window",
                 "is_nakba_day", "is_ashura", "is_yom_kippur", "is_friday",
                 "day_sin", "day_cos", "month_sin", "month_cos"],
    "economic": ["lbp_usd_parallel", "lbp_change_7d", "lbp_change_30d",
                 "lbp_volatility_7d"],
    "food_security": ["ipc_phase_lb", "ipc_phase_sy", "ipc_phase_max",
                      "ipc_crisis_flag", "ipc_phase_change_lb", "ipc_phase_change_sy"],
    "gtrends": ["gtrends_callup_order_il", "gtrends_reserves_il",
                "gtrends_home_front_il", "gtrends_shelter_he_il",
                "gtrends_shelter_ar_lb", "gtrends_war_ar_lb",
                "gtrends_shelling_ar_lb", "gtrends_shelter_ar_sy",
                "gtrends_war_ar_sy", "gtrends_shelling_ar_sy"],
    "interactions": ["hostility_x_neighbor_danger", "ntl_drop_x_fire",
                     "economic_stress", "hostility_x_sirens"],
    "regime": ["post_oct7"],
    "population": ["population_best", "worldpop_population",
                    "hospital_count", "school_count"],
    "conflict_rolling": [
        "dangerous_roll3d", "dangerous_roll7d", "dangerous_roll14d",
        "fatalities_roll3d", "fatalities_roll7d", "fatalities_roll14d",
        "event_roll3d", "event_roll7d", "event_roll14d",
    ],
    "conflict_velocity": [
        "dangerous_delta", "fatality_delta", "dangerous_velocity",
        "fatality_velocity", "actor_pair_delta", "actor_pair_velocity",
    ],
}

# ── Backtests ─────────────────────────────────────────────────
BACKTESTS = [
    {
        "name": "Oct 7 Aftermath — Northern Israel",
        "event_date": "2023-10-07",
        "lat_min": 32.8, "lat_max": 33.5, "lon_min": 35.0, "lon_max": 35.9,
        "needs_retrain": True,
        "retrain_cutoff": "2023-09-01",
    },
    {
        "name": "Lebanon 2024 Escalation",
        "event_date": "2024-09-17",
        "lat_min": 33.0, "lat_max": 33.8, "lon_min": 35.2, "lon_max": 36.2,
        "needs_retrain": True,
        "retrain_cutoff": "2024-08-01",
    },
]


def _available(feature_list, df):
    return [f for f in feature_list if f in df.columns]


def _train_model(X_train, y_train, X_test=None, y_test=None, verbose=0):
    """Train a single XGBoost model with standard hyperparams."""
    n_pos = max((y_train == 1).sum(), 1)
    scale = (y_train == 0).sum() / n_pos
    model = xgb.XGBClassifier(
        n_estimators=500, max_depth=5, learning_rate=0.05,
        scale_pos_weight=scale, subsample=0.7, colsample_bytree=0.7,
        min_child_weight=10, eval_metric="aucpr",
        early_stopping_rounds=30 if X_test is not None else None,
        random_state=RANDOM_SEED,
    )
    # Convert to numpy to avoid XGBoost 3.2/pandas compat issues
    X_tr = X_train.values if hasattr(X_train, 'values') else X_train
    y_tr = y_train.values if hasattr(y_train, 'values') else y_train
    if X_test is not None:
        X_te = X_test.values if hasattr(X_test, 'values') else X_test
        y_te = y_test.values if hasattr(y_test, 'values') else y_test
        eval_set = [(X_te, y_te)]
    else:
        eval_set = None
    model.fit(X_tr, y_tr, eval_set=eval_set, verbose=verbose)
    return model


def evaluate_metrics(y_true, preds, model_name):
    """Compute and print comprehensive metrics."""
    aucpr = average_precision_score(y_true, preds)
    logloss = log_loss(y_true, preds)
    brier = brier_score_loss(y_true, preds)

    prec_arr, rec_arr, thresh = precision_recall_curve(y_true, preds)
    f1_arr = 2 * prec_arr * rec_arr / (prec_arr + rec_arr + 1e-8)
    best_idx = np.argmax(f1_arr)
    best_thresh = thresh[min(best_idx, len(thresh) - 1)]

    y_pred = (preds >= best_thresh).astype(int)
    prec = precision_score(y_true, y_pred, zero_division=0)
    rec = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)

    print(f"\n{'='*55}")
    print(f"  {model_name}")
    print(f"{'='*55}")
    print(f"  AUC-PR:          {aucpr:.4f}")
    print(f"  Log Loss:        {logloss:.4f}")
    print(f"  Brier Score:     {brier:.6f}")
    print(f"  Best Threshold:  {best_thresh:.3f}")
    print(f"  Precision:       {prec:.4f}")
    print(f"  Recall:          {rec:.4f}")
    print(f"  F1:              {f1:.4f}")
    print(f"  Positives:       {int(y_true.sum())} / {len(y_true)} ({100*y_true.mean():.2f}%)")

    return {"aucpr": aucpr, "logloss": logloss, "brier": brier,
            "threshold": best_thresh, "precision": prec, "recall": rec, "f1": f1}


def plot_calibration(y_true, preds, model_name, filepath):
    """Reliability diagram + score distribution."""
    _, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    try:
        prob_true, prob_pred = calibration_curve(y_true, preds, n_bins=10, strategy="uniform")
        ax1.plot(prob_pred, prob_true, "o-", color="#e63946", label=model_name, linewidth=2)
    except ValueError:
        ax1.text(0.5, 0.5, "Insufficient data for calibration", ha="center", va="center")
    ax1.plot([0, 1], [0, 1], "--", color="gray", label="Perfect")
    ax1.set_xlabel("Mean predicted probability")
    ax1.set_ylabel("Fraction of positives")
    ax1.set_title(f"Calibration — {model_name}")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    ax2.hist(preds[y_true == 0], bins=50, alpha=0.5, label="Negative", color="#457b9d")
    ax2.hist(preds[y_true == 1], bins=50, alpha=0.5, label="Positive", color="#e63946")
    ax2.set_xlabel("Predicted probability")
    ax2.set_ylabel("Count")
    ax2.set_title(f"Score Distribution — {model_name}")
    ax2.legend()
    ax2.set_yscale("log")
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(filepath, dpi=150)
    plt.clf()
    plt.close()


def plot_shap(model, X_sample, model_name, filepath):
    """SHAP summary plot with stratified sampling."""
    explainer = shap.TreeExplainer(model)
    # Convert to numpy to avoid XGBoost 3.2/pandas compatibility issue
    X_np = X_sample.values if hasattr(X_sample, 'values') else X_sample
    shap_values = explainer.shap_values(X_np)
    col_names = list(X_sample.columns) if hasattr(X_sample, 'columns') else None
    shap.summary_plot(shap_values, X_np, feature_names=col_names, show=False)
    plt.title(f"{model_name} — Feature Importance")
    plt.tight_layout()
    plt.savefig(filepath, dpi=150)
    plt.clf()
    plt.close()


# ── Walk-Forward Cross-Validation ─────────────────────────────

def walk_forward_cv(master_df, _all_features=None):
    """Expanding-window walk-forward CV with temporal gap."""
    print("\n" + "=" * 55)
    print("  WALK-FORWARD CROSS-VALIDATION (6 quarterly folds)")
    print("=" * 55)

    onset_results = []
    cont_results = []

    for fold in CV_FOLDS:
        train_end = pd.Timestamp(fold["train_end"])
        test_start = pd.Timestamp(fold["test_start"])
        test_end = pd.Timestamp(fold["test_end"])

        train = master_df[master_df["date"] <= train_end]
        test = master_df[(master_df["date"] >= test_start) & (master_df["date"] <= test_end)]

        if len(test) == 0:
            print(f"\n  {fold['name']}: No test data, skipping")
            continue

        # Split into onset/continuation
        onset_train = train[train["dangerous_roll14d"] == 0]
        onset_test = test[test["dangerous_roll14d"] == 0]
        cont_train = train[train["dangerous_roll14d"] > 0]
        cont_test = test[test["dangerous_roll14d"] > 0]

        o_feats = _available(ONSET_FEATURES, onset_train)
        c_feats = _available(CONT_FEATURES, cont_train)

        print(f"\n  Fold {fold['name']}:")
        print(f"    Train: ≤{fold['train_end']}, Test: {fold['test_start']} → {fold['test_end']}")

        # Train + evaluate onset
        if len(onset_test) > 0 and onset_test["label"].sum() > 0:
            o_model = _train_model(
                onset_train[o_feats].fillna(0), onset_train["label"])
            o_preds = o_model.predict_proba(onset_test[o_feats].fillna(0).values)[:, 1]
            o_aucpr = average_precision_score(onset_test["label"], o_preds)
            onset_results.append({"fold": fold["name"], "aucpr": o_aucpr,
                                  "n_test": len(onset_test), "n_pos": int(onset_test["label"].sum())})
            print(f"    Onset:  AUC-PR={o_aucpr:.4f}  ({onset_test['label'].sum()} pos / {len(onset_test)} total)")
        else:
            print(f"    Onset:  Skipped (no positives in test)")

        # Train + evaluate continuation
        if len(cont_test) > 0 and cont_test["label"].sum() > 0:
            c_model = _train_model(
                cont_train[c_feats].fillna(0), cont_train["label"])
            c_preds = c_model.predict_proba(cont_test[c_feats].fillna(0).values)[:, 1]
            c_aucpr = average_precision_score(cont_test["label"], c_preds)
            cont_results.append({"fold": fold["name"], "aucpr": c_aucpr,
                                 "n_test": len(cont_test), "n_pos": int(cont_test["label"].sum())})
            print(f"    Cont:   AUC-PR={c_aucpr:.4f}  ({cont_test['label'].sum()} pos / {len(cont_test)} total)")
        else:
            print(f"    Cont:   Skipped (no positives in test)")

    # Summary
    if onset_results:
        o_scores = [r["aucpr"] for r in onset_results]
        print(f"\n  Onset CV Summary:  mean={np.mean(o_scores):.4f} ± {np.std(o_scores):.4f}")
    if cont_results:
        c_scores = [r["aucpr"] for r in cont_results]
        print(f"  Cont CV Summary:   mean={np.mean(c_scores):.4f} ± {np.std(c_scores):.4f}")

    return onset_results, cont_results


# ── Feature Ablation ──────────────────────────────────────────

def feature_ablation(master_df, baseline_onset_aucpr, baseline_cont_aucpr):
    """Remove each feature group and measure AUC-PR drop."""
    print("\n" + "=" * 55)
    print("  FEATURE ABLATION (remove each group, measure impact)")
    print("=" * 55)

    train_end = pd.Timestamp(TRAIN_CUTOFF)
    test_start_ts = pd.Timestamp(TEST_START)

    train = master_df[master_df["date"] <= train_end]
    test = master_df[master_df["date"] >= test_start_ts]

    onset_train = train[train["dangerous_roll14d"] == 0]
    onset_test = test[test["dangerous_roll14d"] == 0]
    cont_train = train[train["dangerous_roll14d"] > 0]
    cont_test = test[test["dangerous_roll14d"] > 0]

    o_feats_all = _available(ONSET_FEATURES, onset_train)
    c_feats_all = _available(CONT_FEATURES, cont_train)

    results = []
    for group_name, group_cols in ABLATION_GROUPS.items():
        o_feats = [f for f in o_feats_all if f not in group_cols]
        c_feats = [f for f in c_feats_all if f not in group_cols]

        o_removed = len(o_feats_all) - len(o_feats)
        c_removed = len(c_feats_all) - len(c_feats)

        o_aucpr = None
        if o_feats and len(onset_test) > 0 and onset_test["label"].sum() > 0:
            m = _train_model(onset_train[o_feats].fillna(0), onset_train["label"])
            p = m.predict_proba(onset_test[o_feats].fillna(0).values)[:, 1]
            o_aucpr = average_precision_score(onset_test["label"], p)

        c_aucpr = None
        if c_feats and len(cont_test) > 0 and cont_test["label"].sum() > 0:
            m = _train_model(cont_train[c_feats].fillna(0), cont_train["label"])
            p = m.predict_proba(cont_test[c_feats].fillna(0).values)[:, 1]
            c_aucpr = average_precision_score(cont_test["label"], p)

        o_delta = (baseline_onset_aucpr - o_aucpr) if o_aucpr else None
        c_delta = (baseline_cont_aucpr - c_aucpr) if c_aucpr else None

        results.append({
            "group": group_name,
            "onset_aucpr": o_aucpr, "onset_delta": o_delta,
            "cont_aucpr": c_aucpr, "cont_delta": c_delta,
            "onset_removed": o_removed, "cont_removed": c_removed,
        })

        o_str = f"AUC-PR={o_aucpr:.4f} (Δ={o_delta:+.4f})" if o_aucpr else "N/A"
        c_str = f"AUC-PR={c_aucpr:.4f} (Δ={c_delta:+.4f})" if c_aucpr else "N/A"
        print(f"  -{group_name:20s}  Onset: {o_str}  |  Cont: {c_str}")

    return results


# ── Backtests ─────────────────────────────────────────────────

def run_backtests(master_df, main_onset, main_cont, onset_feats, cont_feats):
    """Backtests with out-of-sample retraining for in-sample events."""
    print("\n" + "=" * 55)
    print("  BACKTESTS")
    print("=" * 55)

    unique_hexes = master_df["h3_id"].unique()
    centroids = {hid: h3.cell_to_latlng(hid) for hid in unique_hexes}
    master_df = master_df.copy()
    master_df["lat"] = master_df["h3_id"].map(lambda x: centroids[x][0])
    master_df["lon"] = master_df["h3_id"].map(lambda x: centroids[x][1])

    os.makedirs(MODEL_DIR, exist_ok=True)

    for bt in BACKTESTS:
        event_date = pd.Timestamp(bt["event_date"])
        w_start = event_date - pd.Timedelta(days=45)
        w_end = event_date + pd.Timedelta(days=15)

        area = master_df[
            (master_df["lat"] >= bt["lat_min"]) & (master_df["lat"] <= bt["lat_max"]) &
            (master_df["lon"] >= bt["lon_min"]) & (master_df["lon"] <= bt["lon_max"]) &
            (master_df["date"] >= w_start) & (master_df["date"] <= w_end)
        ].copy()

        if len(area) == 0:
            print(f"  {bt['name']}: No data")
            continue

        # Filter features to what exists in the backtest data
        bt_onset_feats = _available(onset_feats, area)
        bt_cont_feats = _available(cont_feats, area)

        if bt["needs_retrain"]:
            cutoff = pd.Timestamp(bt["retrain_cutoff"])
            pre = master_df[master_df["date"] <= cutoff]
            o_train = pre[pre["dangerous_roll14d"] == 0]
            c_train = pre[pre["dangerous_roll14d"] > 0]
            o_f = _available(bt_onset_feats, o_train)
            c_f = _available(bt_cont_feats, c_train)
            o_model = _train_model(o_train[o_f].fillna(0), o_train["label"])
            c_model = _train_model(c_train[c_f].fillna(0), c_train["label"])
            tag = "OUT-OF-SAMPLE (retrained)"
            print(f"  {bt['name']}: retrained on ≤{bt['retrain_cutoff']} ({len(o_f)} feats)")
        else:
            o_model, c_model = main_onset, main_cont
            o_f = _available(bt_onset_feats, area)
            c_f = _available(bt_cont_feats, area)
            tag = "OUT-OF-SAMPLE"

        onset_rows = area[area["dangerous_roll14d"] == 0]
        cont_rows = area[area["dangerous_roll14d"] > 0]
        preds = pd.Series(np.nan, index=area.index)

        if len(onset_rows) > 0:
            preds.loc[onset_rows.index] = o_model.predict_proba(
                onset_rows[o_f].fillna(0).values)[:, 1]
        if len(cont_rows) > 0:
            preds.loc[cont_rows.index] = c_model.predict_proba(
                cont_rows[c_f].fillna(0).values)[:, 1]

        area["pred"] = preds
        daily = area.groupby("date")["pred"].mean().reset_index()

        _, ax = plt.subplots(figsize=(12, 5))
        ax.plot(daily["date"], daily["pred"], color="#e63946", linewidth=2)
        ax.axvline(event_date, color="black", linestyle="--", linewidth=1.5,
                   label=f"Event: {bt['event_date']}")
        ax.fill_between(daily["date"], daily["pred"], alpha=0.15, color="#e63946")
        ax.set_title(f"Backtest: {bt['name']}  [{tag}]", fontsize=14)
        ax.set_xlabel("Date")
        ax.set_ylabel("Average Risk Probability")
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.tight_layout()

        slug = bt["name"].lower().replace(" ", "_").replace("—", "").replace("/", "_").replace("__", "_")
        fname = os.path.join(MODEL_DIR, f"backtest_{slug}.png")
        plt.savefig(fname, dpi=150)
        plt.clf()
        plt.close()
        print(f"  Saved: {fname}")


# ── Main Evaluation ───────────────────────────────────────────

def evaluate_models():
    print("Loading models and data...")

    onset_model = xgb.XGBClassifier()
    onset_model.load_model(os.path.join(MODEL_DIR, "xgb_onset.ubj"))
    cont_model = xgb.XGBClassifier()
    cont_model.load_model(os.path.join(MODEL_DIR, "xgb_continuation.ubj"))

    onset_df = pd.read_parquet(os.path.join(BASE_DIR, "data", "processed", "onset_set.parquet"))
    cont_df = pd.read_parquet(os.path.join(BASE_DIR, "data", "processed", "continuation_set.parquet"))

    onset_feats = _available(ONSET_FEATURES, onset_df)
    cont_feats = _available(CONT_FEATURES, cont_df)
    print(f"Onset features: {len(onset_feats)}, Continuation features: {len(cont_feats)}")

    test_start = pd.Timestamp(TEST_START)
    onset_test = onset_df[onset_df["date"] >= test_start]
    cont_test = cont_df[cont_df["date"] >= test_start]
    print(f"Onset test: {len(onset_test):,} rows, Continuation test: {len(cont_test):,} rows")

    print(f"Label horizon: {LABEL_HORIZON_DAYS} days")

    # ── 1. Comprehensive Metrics ──────────────────────────────
    onset_preds = onset_model.predict_proba(onset_test[onset_feats].fillna(0).values)[:, 1]
    cont_preds = cont_model.predict_proba(cont_test[cont_feats].fillna(0).values)[:, 1]

    onset_metrics = evaluate_metrics(onset_test["label"].values, onset_preds,
                                     f"Onset Model (standard, {LABEL_HORIZON_DAYS}d horizon)")
    cont_metrics = evaluate_metrics(cont_test["label"].values, cont_preds,
                                     f"Continuation Model ({LABEL_HORIZON_DAYS}d horizon)")

    # ── 1b. Focal Loss onset comparison ──────────────────────
    focal_path = os.path.join(MODEL_DIR, "xgb_onset_focal.ubj")
    focal_metrics = None
    if os.path.exists(focal_path):
        print("\n  Loading focal loss onset model for comparison...")
        focal_booster = xgb.Booster()
        focal_booster.load_model(focal_path)
        dtest_onset = xgb.DMatrix(onset_test[onset_feats].fillna(0))
        focal_preds = expit(focal_booster.predict(dtest_onset))
        focal_metrics = evaluate_metrics(
            onset_test["label"].values, focal_preds,
            f"Onset Model (FOCAL LOSS, {LABEL_HORIZON_DAYS}d horizon)")
    else:
        print("  No focal loss model found, skipping comparison")

    os.makedirs(MODEL_DIR, exist_ok=True)

    # ── 2. Calibration Plots ──────────────────────────────────
    print("\nGenerating calibration plots...")
    plot_calibration(onset_test["label"].values, onset_preds,
                     "Onset Model", os.path.join(MODEL_DIR, "calibration_onset.png"))
    plot_calibration(cont_test["label"].values, cont_preds,
                     "Continuation Model", os.path.join(MODEL_DIR, "calibration_continuation.png"))

    # ── 3. SHAP (stratified) ─────────────────────────────────
    print("Generating SHAP plots...")
    for name, test_data, feats, model, fname in [
        ("Onset", onset_test, onset_feats, onset_model, "shap_onset.png"),
        ("Continuation", cont_test, cont_feats, cont_model, "shap_continuation.png"),
    ]:
        pos = test_data[test_data["label"] == 1]
        neg = test_data[test_data["label"] == 0]
        n_pos = min(len(pos), 250)
        n_neg = min(len(neg), 250)
        sample = pd.concat([
            pos.sample(n=n_pos, random_state=RANDOM_SEED) if n_pos > 0 else pos,
            neg.sample(n=n_neg, random_state=RANDOM_SEED),
        ])
        plot_shap(model, sample[feats].fillna(0), f"{name} Model",
                  os.path.join(MODEL_DIR, fname))
        print(f"  {fname} ({n_pos} pos + {n_neg} neg)")

    # ── 4. Walk-Forward CV ────────────────────────────────────
    master = pd.concat([onset_df, cont_df]).sort_values(["h3_id", "date"])
    cv_onset, cv_cont = walk_forward_cv(master, onset_feats + cont_feats)

    # ── 5. Feature Ablation ───────────────────────────────────
    ablation = feature_ablation(master, onset_metrics["aucpr"], cont_metrics["aucpr"])

    # ── 6. Backtests ──────────────────────────────────────────
    csv_path = os.path.join(BASE_DIR, "data", "processed", "acled_h3_gdelt_firms_weather.csv")
    master_full = pd.read_csv(csv_path, parse_dates=["event_date"])
    master_full = master_full.rename(columns={"event_date": "date"})
    run_backtests(master_full, onset_model, cont_model, onset_feats, cont_feats)

    # ── 7. Save Report ────────────────────────────────────────
    report_lines = [
        "Sentinel v2 Evaluation Report",
        "=" * 50,
        f"Train cutoff: {TRAIN_CUTOFF}  |  Test start: {TEST_START}",
        f"Label horizon: {LABEL_HORIZON_DAYS} days",
        "",
        "ONSET MODEL (standard)",
        f"  AUC-PR:     {onset_metrics['aucpr']:.4f}",
        f"  Log Loss:   {onset_metrics['logloss']:.4f}",
        f"  Brier:      {onset_metrics['brier']:.6f}",
        f"  Best F1:    {onset_metrics['f1']:.4f} @ threshold {onset_metrics['threshold']:.3f}",
        f"  Precision:  {onset_metrics['precision']:.4f}",
        f"  Recall:     {onset_metrics['recall']:.4f}",
        f"  Features:   {len(onset_feats)}",
    ]
    if focal_metrics:
        report_lines += [
            "",
            "ONSET MODEL (focal loss)",
            f"  AUC-PR:     {focal_metrics['aucpr']:.4f}",
            f"  Log Loss:   {focal_metrics['logloss']:.4f}",
            f"  Brier:      {focal_metrics['brier']:.6f}",
            f"  Best F1:    {focal_metrics['f1']:.4f} @ threshold {focal_metrics['threshold']:.3f}",
            f"  Precision:  {focal_metrics['precision']:.4f}",
            f"  Recall:     {focal_metrics['recall']:.4f}",
        ]
    report_lines += [
        "",
        "CONTINUATION MODEL",
        f"  AUC-PR:     {cont_metrics['aucpr']:.4f}",
        f"  Log Loss:   {cont_metrics['logloss']:.4f}",
        f"  Brier:      {cont_metrics['brier']:.6f}",
        f"  Best F1:    {cont_metrics['f1']:.4f} @ threshold {cont_metrics['threshold']:.3f}",
        f"  Precision:  {cont_metrics['precision']:.4f}",
        f"  Recall:     {cont_metrics['recall']:.4f}",
        f"  Features:   {len(cont_feats)}",
        "",
        "WALK-FORWARD CV",
    ]
    if cv_onset:
        scores = [r["aucpr"] for r in cv_onset]
        report_lines.append(f"  Onset:  mean={np.mean(scores):.4f} ± {np.std(scores):.4f}")
        for r in cv_onset:
            report_lines.append(f"    {r['fold']}: AUC-PR={r['aucpr']:.4f} ({r['n_pos']} pos / {r['n_test']} total)")
    if cv_cont:
        scores = [r["aucpr"] for r in cv_cont]
        report_lines.append(f"  Cont:   mean={np.mean(scores):.4f} ± {np.std(scores):.4f}")
        for r in cv_cont:
            report_lines.append(f"    {r['fold']}: AUC-PR={r['aucpr']:.4f} ({r['n_pos']} pos / {r['n_test']} total)")

    report_lines.append("")
    report_lines.append("FEATURE ABLATION (positive Δ = removing group hurts performance)")
    for r in ablation:
        o = f"Δ={r['onset_delta']:+.4f}" if r["onset_delta"] is not None else "N/A"
        c = f"Δ={r['cont_delta']:+.4f}" if r["cont_delta"] is not None else "N/A"
        report_lines.append(f"  -{r['group']:20s}  Onset: {o}  |  Cont: {c}")

    report_lines.append(f"\nOnset features: {onset_feats}")
    report_lines.append(f"Cont features: {cont_feats}")

    report_path = os.path.join(MODEL_DIR, "eval_report.txt")
    with open(report_path, "w") as f:
        f.write("\n".join(report_lines))
    print(f"\nSaved: {report_path}")


if __name__ == "__main__":
    evaluate_models()
