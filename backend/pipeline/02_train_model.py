"""
Step 2: XGBoost Model Training
Trains a binary classifier to predict escalation in the next week for a given H3 hex.
Auto-detects the richest available feature file (ACLED+GDELT+FIRMS > ACLED+GDELT > ACLED only).
Output: models/xgb_sentinel.ubj  (model)  +  models/eval_report.txt
"""

import pandas as pd
import numpy as np
import xgboost as xgb
from scipy.special import expit
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import (
    classification_report, roc_auc_score,
    precision_recall_curve, average_precision_score,
    f1_score, precision_score, recall_score
)
import matplotlib.pyplot as plt
import os

# ── Config ────────────────────────────────────────────────────────────────────
# Use richest available data file
for candidate in [
    "data/processed/acled_h3_gdelt_firms_weather.csv",
    "data/processed/acled_h3_gdelt_firms.csv",
    "data/processed/acled_h3_gdelt.csv",
    "data/processed/acled_h3.csv",
]:
    if os.path.exists(candidate):
        PROCESSED_PATH = candidate
        break

MODEL_OUT  = "models/xgb_sentinel.ubj"
REPORT_OUT = "models/eval_report.txt"
PLOT_OUT   = "models/feature_importance.png"

# Base features always present (daily grain)
BASE_FEATURES = [
    "event_count",
    "dangerous_count",
    "total_fatalities",
    "max_fatalities",
    "battle_count",
    "explosion_count",
    "vac_count",
    "riot_count",
    "population_best",
    "unique_actors",
    # Rolling windows: 3d, 7d, 14d
    "dangerous_roll3d",
    "dangerous_roll7d",
    "dangerous_roll14d",
    "fatalities_roll3d",
    "fatalities_roll7d",
    "fatalities_roll14d",
    "event_roll3d",
    "event_roll7d",
    "event_roll14d",
    # Velocity / momentum
    "dangerous_delta",
    "fatality_delta",
    "dangerous_velocity",
    "fatality_velocity",
    # Spatial lag
    "neighbor_danger_avg",
    "neighbor_fatal_sum",
    # Actor novelty
    "actor_pair_count",
    "actor_pair_delta",
    "actor_pair_velocity",
    # Temporal lag (yesterday / 2 days ago — self-referential signal)
    "dangerous_lag1",
    "dangerous_lag2",
    "fatalities_lag1",
    "battle_lag1",
    "explosion_lag1",
]

# GDELT features (available after 03_ingest_gdelt.py)
GDELT_FEATURES = [
    "gdelt_event_count",
    "gdelt_avg_tone",
    "gdelt_min_goldstein",
    "gdelt_avg_goldstein",
    "gdelt_num_articles",
    "gdelt_hostility",
    "neighbor_gdelt_hostility_avg",  # spatial lag: ring-1 news hostility bleed
]

# FIRMS features (available after 04_ingest_firms.py)
FIRMS_FEATURES = [
    "firms_hotspot_count",
    "firms_avg_frp",
    "firms_max_frp",
    "firms_spike",
    "neighbor_firms_spike_sum",
]

# GDELT CAMEO event-type features (available after re-running 03_ingest_gdelt.py)
GDELT_CAMEO_FEATURES = [
    "gdelt_protest_count",
    "gdelt_threaten_count",
    "gdelt_assault_count",
    "gdelt_fight_count",
    "gdelt_cameo_conflict",
    "neighbor_gdelt_protest_avg",
]

# Weather features (available after 05_ingest_weather.py)
WEATHER_FEATURES = [
    "temp_max",
    "temp_anomaly_30d",
    "precip_mm",
    "precip_spike",
]

LABEL = "label"

# ── Load ──────────────────────────────────────────────────────────────────────
print(f"Loading {PROCESSED_PATH}...")
df = pd.read_csv(PROCESSED_PATH, parse_dates=["event_date"])
df = df.sort_values(["h3_id", "event_date"]).reset_index(drop=True)

# ── Temporal Lag Features (self-referential) ─────────────────────────────────
# Yesterday's and 2-days-ago activity per hex — strong predictor since conflict
# clusters temporally. Computed here to avoid re-running the full pipeline.
print("Computing temporal lag features...")
for col, shift_n, new_col in [
    ("dangerous_count",  1, "dangerous_lag1"),
    ("dangerous_count",  2, "dangerous_lag2"),
    ("total_fatalities", 1, "fatalities_lag1"),
    ("battle_count",     1, "battle_lag1"),
    ("explosion_count",  1, "explosion_lag1"),
]:
    df[new_col] = df.groupby("h3_id")[col].shift(shift_n).fillna(0)

# ── Relabel: 72h lookahead ────────────────────────────────────────────────────
# Override stored label with 72h window directly from dangerous_count.
# This avoids re-running the full 2-hour preprocessing pipeline.
print("Relabeling to 72h lookahead (t+1, t+2, t+3)...")
df["_l1"] = df.groupby("h3_id")["dangerous_count"].shift(-1).fillna(0)
df["_l2"] = df.groupby("h3_id")["dangerous_count"].shift(-2).fillna(0)
df["_l3"] = df.groupby("h3_id")["dangerous_count"].shift(-3).fillna(0)
df[LABEL] = (df[["_l1", "_l2", "_l3"]].max(axis=1) > 0).astype(int)
df = df.drop(columns=["_l1", "_l2", "_l3"])
# Drop last 3 days per hex (no valid 72h window)
df["_rank_end"] = df.groupby("h3_id").cumcount(ascending=False)
df = df[df["_rank_end"] >= 3].drop(columns=["_rank_end"])

df = df.sort_values("event_date").reset_index(drop=True)

# ── Active Hex Filter ─────────────────────────────────────────────────────────
# Only keep hex-days with recent dangerous signal. "Quiet" hexes (no events in
# 14d window, no dangerous yesterday, no hot neighbors) are pre-classified as
# CLEAR by the scoring pipeline and never reach the ML model. Training on
# active hexes only raises the positive base rate 1.5% → ~11%, which lets the
# model learn real boundaries instead of fighting overwhelming class imbalance.
print("Filtering to active hexes (recent dangerous signal)...")
df["_active"] = (
    (df["dangerous_roll14d"]   > 0) |
    (df["dangerous_lag1"]      > 0) |
    (df["neighbor_danger_avg"] > 0)
)
n_all = len(df)
df = df[df["_active"]].drop(columns=["_active"]).reset_index(drop=True)
print(f"  Kept {len(df):,} / {n_all:,} rows ({len(df)/n_all*100:.1f}% active)")

print(f"  Rows: {len(df):,}  |  Hexes: {df['h3_id'].nunique():,}")
print(f"  Label balance (72h, active only): {df[LABEL].value_counts(normalize=True).round(3).to_dict()}")

# Dynamically include only features present in this file
FEATURES = BASE_FEATURES.copy()
for col in GDELT_FEATURES + FIRMS_FEATURES + GDELT_CAMEO_FEATURES + WEATHER_FEATURES:
    if col in df.columns:
        FEATURES.append(col)

gdelt_active   = any(c in df.columns for c in GDELT_FEATURES)
firms_active   = any(c in df.columns for c in FIRMS_FEATURES)
cameo_active   = any(c in df.columns for c in GDELT_CAMEO_FEATURES)
weather_active = any(c in df.columns for c in WEATHER_FEATURES)
print(f"  Feature set: base"
      f"{' + GDELT' if gdelt_active else ''}"
      f"{' + FIRMS' if firms_active else ''}"
      f"{' + CAMEO' if cameo_active else ''}"
      f"{' + weather' if weather_active else ''}"
      f" ({len(FEATURES)} features total)")

X = df[FEATURES].fillna(0)
y = df[LABEL]

# ── Imbalance weight ──────────────────────────────────────────────────────────
neg, pos = (y == 0).sum(), (y == 1).sum()
scale_pos_weight = neg / pos
print(f"\n  scale_pos_weight = {scale_pos_weight:.2f}  ({neg} neg / {pos} pos)")

# ── Time-Series Cross Validation ──────────────────────────────────────────────
# Use TimeSeriesSplit to respect temporal ordering — never train on future data.
tscv = TimeSeriesSplit(n_splits=5)

print("\nRunning 5-fold time-series cross-validation...")

fold_aucs, fold_aps = [], []

for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
    X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
    y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

    model = xgb.XGBClassifier(
        n_estimators=400,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        tree_method="hist",
        nthread=-1,
        eval_metric="aucpr",
        early_stopping_rounds=30,
        random_state=42,
        verbosity=0,
    )
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=False,
    )

    proba = model.predict_proba(X_val)[:, 1]
    auc = roc_auc_score(y_val, proba)
    ap  = average_precision_score(y_val, proba)
    fold_aucs.append(auc)
    fold_aps.append(ap)
    print(f"  Fold {fold+1}: ROC-AUC = {auc:.3f}  |  Avg Precision = {ap:.3f}")

print(f"\n  Mean ROC-AUC:        {np.mean(fold_aucs):.3f} ± {np.std(fold_aucs):.3f}")
print(f"  Mean Avg Precision:  {np.mean(fold_aps):.3f} ± {np.std(fold_aps):.3f}")

# ── Final Model: Train on All Data ────────────────────────────────────────────
print("\nTraining final model on full dataset...")

# Hold out last 10% for final evaluation report
split_idx = int(len(X) * 0.9)
X_train_f, X_test_f = X.iloc[:split_idx], X.iloc[split_idx:]
y_train_f, y_test_f = y.iloc[:split_idx], y.iloc[split_idx:]

final_model = xgb.XGBClassifier(
    n_estimators=400,
    max_depth=5,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    scale_pos_weight=scale_pos_weight,
    tree_method="hist",
    nthread=-1,
    eval_metric="aucpr",
    early_stopping_rounds=30,
    random_state=42,
    verbosity=0,
)
final_model.fit(
    X_train_f, y_train_f,
    eval_set=[(X_test_f, y_test_f)],
    verbose=False,
)

# ── Evaluate Standard Model ───────────────────────────────────────────────────
std_prob = final_model.predict_proba(X_test_f)[:, 1]
std_auc  = roc_auc_score(y_test_f, std_prob)
std_ap   = average_precision_score(y_test_f, std_prob)
print(f"\nStandard model — ROC-AUC: {std_auc:.3f}  |  AUC-PR: {std_ap:.3f}")

# ── Focal Loss Model ──────────────────────────────────────────────────────────
# Focal loss down-weights easy negatives, forcing the model to focus on hard
# positives. Key for severe class imbalance (standard fix in object detection).
FOCAL_GAMMA = 2.0   # focusing strength: higher = more focus on hard examples
FOCAL_ALPHA = 0.25  # weight for positive class (lower α + high γ is the sweet spot)

def focal_loss_obj(y_pred, dtrain):
    """Gradient and Hessian of focal loss for XGBoost custom objective."""
    y_true   = dtrain.get_label()
    p        = np.clip(expit(y_pred), 1e-7, 1 - 1e-7)
    pt       = np.where(y_true == 1, p, 1 - p)          # prob of true class
    alpha_t  = np.where(y_true == 1, FOCAL_ALPHA, 1 - FOCAL_ALPHA)
    focal_wt = alpha_t * (1 - pt) ** FOCAL_GAMMA        # down-weight easy examples
    grad     = focal_wt * (p - y_true)                  # reweighted BCE gradient
    hess     = np.maximum(focal_wt * p * (1 - p), 1e-6)
    return grad, hess

print("\nTraining Focal Loss model (gamma=2, alpha=0.25)...")
dtrain_f = xgb.DMatrix(X_train_f, label=y_train_f, feature_names=FEATURES)
dtest_f  = xgb.DMatrix(X_test_f,  label=y_test_f,  feature_names=FEATURES)

focal_booster = xgb.train(
    {
        "max_depth": 5,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "tree_method": "hist",
        "nthread": -1,
        "disable_default_eval_metric": True,
        "seed": 42,
    },
    dtrain_f,
    num_boost_round=400,
    obj=focal_loss_obj,
    evals=[(dtest_f, "test")],
    verbose_eval=False,
)
# Custom objective outputs raw logits — apply sigmoid to get probabilities
fcl_prob = expit(focal_booster.predict(dtest_f))
fcl_auc  = roc_auc_score(y_test_f, fcl_prob)
fcl_ap   = average_precision_score(y_test_f, fcl_prob)
print(f"Focal model   — ROC-AUC: {fcl_auc:.3f}  |  AUC-PR: {fcl_ap:.3f}")

# ── Fine-grained Threshold Sweep & Comparison ─────────────────────────────────
THRESHOLDS = np.arange(0.10, 0.96, 0.05)
n_days = max(
    (df["event_date"].iloc[split_idx:].max() -
     df["event_date"].iloc[split_idx:].min()).days, 1
)

def threshold_sweep(proba, y_true, label):
    print(f"\n{'─'*70}")
    print(f"  {label}")
    print(f"{'─'*70}")
    print(f"{'Thresh':>8} {'Prec':>8} {'Recall':>8} {'F1':>8} {'Alerts/day':>12}")
    print(f"{'─'*70}")
    best_row, best_f1 = None, -1
    for t in THRESHOLDS:
        pred = (proba >= t).astype(int)
        if pred.sum() == 0:
            continue
        p  = precision_score(y_true, pred, zero_division=0)
        r  = recall_score(y_true, pred, zero_division=0)
        f1 = f1_score(y_true, pred, zero_division=0)
        apd = pred.sum() / n_days
        flag = " ◀ best F1" if f1 > best_f1 else ""
        if f1 > best_f1:
            best_f1 = f1
            best_row = (t, p, r, f1, apd)
        print(f"{t:>8.2f} {p:>8.3f} {r:>8.3f} {f1:>8.3f} {apd:>12.1f}{flag}")
    return best_row

best_std = threshold_sweep(std_prob,  y_test_f, "STANDARD XGBoost (scale_pos_weight)")
best_fcl = threshold_sweep(fcl_prob,  y_test_f, "FOCAL LOSS (gamma=2.0, alpha=0.25)")

print(f"\n{'='*70}")
print(f"  BEST OPERATING POINTS")
print(f"{'='*70}")
print(f"{'Model':<30} {'Thresh':>8} {'Prec':>8} {'Recall':>8} {'F1':>8} {'Alerts/day':>12}")
print(f"{'─'*70}")
print(f"{'Standard XGBoost':<30} {best_std[0]:>8.2f} {best_std[1]:>8.3f} {best_std[2]:>8.3f} {best_std[3]:>8.3f} {best_std[4]:>12.1f}")
print(f"{'Focal Loss':<30} {best_fcl[0]:>8.2f} {best_fcl[1]:>8.3f} {best_fcl[2]:>8.3f} {best_fcl[3]:>8.3f} {best_fcl[4]:>12.1f}")
print(f"{'='*70}")

# Pick winner by best F1
best_model_name = "Focal Loss" if best_fcl[3] >= best_std[3] else "Standard XGBoost"
best_threshold  = best_fcl[0] if best_fcl[3] >= best_std[3] else best_std[0]
print(f"\nWinner: {best_model_name} at threshold {best_threshold:.2f}")

# ── Save Models ───────────────────────────────────────────────────────────────
os.makedirs("models", exist_ok=True)
final_model.save_model("models/xgb_standard.ubj")
focal_booster.save_model("models/xgb_focal.ubj")
# Save winner as production model
if best_fcl[3] >= best_std[3]:
    focal_booster.save_model(MODEL_OUT)
else:
    final_model.save_model(MODEL_OUT)
print(f"Standard model saved → models/xgb_standard.ubj")
print(f"Focal model saved    → models/xgb_focal.ubj")
print(f"Production model ({best_model_name}) saved → {MODEL_OUT}")

# ── Save Eval Report ──────────────────────────────────────────────────────────
with open(REPORT_OUT, "w") as f:
    f.write("Sentinel XGBoost — Evaluation Report (72h label)\n")
    f.write("=" * 55 + "\n\n")
    f.write(f"CV Mean ROC-AUC:       {np.mean(fold_aucs):.3f} ± {np.std(fold_aucs):.3f}\n")
    f.write(f"CV Mean Avg Precision: {np.mean(fold_aps):.3f} ± {np.std(fold_aps):.3f}\n\n")
    f.write(f"Standard — ROC-AUC: {std_auc:.3f}  AUC-PR: {std_ap:.3f}\n")
    f.write(f"Focal     — ROC-AUC: {fcl_auc:.3f}  AUC-PR: {fcl_ap:.3f}\n\n")
    f.write(f"Best Standard:  thresh={best_std[0]:.2f}  P={best_std[1]:.3f}  R={best_std[2]:.3f}  F1={best_std[3]:.3f}\n")
    f.write(f"Best Focal:     thresh={best_fcl[0]:.2f}  P={best_fcl[1]:.3f}  R={best_fcl[2]:.3f}  F1={best_fcl[3]:.3f}\n")
    f.write(f"\nProduction model: {best_model_name} @ threshold {best_threshold:.2f}\n")
print(f"Eval report saved → {REPORT_OUT}")

# ── Feature Importance Plot ───────────────────────────────────────────────────
importance = pd.Series(
    final_model.feature_importances_,
    index=FEATURES
).sort_values(ascending=True)

fig, ax = plt.subplots(figsize=(8, 5))
importance.plot(kind="barh", ax=ax, color="#e05c5c")
ax.set_title("Feature Importance — Sentinel XGBoost")
ax.set_xlabel("Gain")
plt.tight_layout()
plt.savefig(PLOT_OUT, dpi=150)
print(f"Feature importance plot saved → {PLOT_OUT}")
