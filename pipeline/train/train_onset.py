"""Train onset model: predict conflict emergence in peaceful hexes.

Trains two variants:
  1. Standard XGBoost with scale_pos_weight (baseline)
  2. Focal loss XGBoost (down-weights easy negatives, focuses on hard cases)
"""
import pandas as pd
import numpy as np
import os
import sys
import xgboost as xgb
from sklearn.metrics import average_precision_score
from scipy.special import expit  # sigmoid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ml.config import TRAIN_CUTOFF, TEST_START, RANDOM_SEED

ONSET_FEATURES = [
    # ── PROVEN BY ABLATION (positive delta when removed) ──────

    # Population/infrastructure (#1: Δ+0.025)
    "population_best", "worldpop_population",
    "hospital_count", "school_count",

    # Spatial ring-1 (#2: Δ+0.015)
    "neighbor_danger_avg", "neighbor_fatal_sum",
    "neighbor_gdelt_hostility_avg", "neighbor_firms_avg",
    "spatial_gradient",

    # GDELT dynamics (#3: Δ+0.010)
    "gdelt_hostility_roll3d", "gdelt_hostility_roll7d", "gdelt_hostility_velocity",
    "gdelt_event_roll3d", "gdelt_event_roll7d", "gdelt_event_velocity",
    "gdelt_tone_delta",

    # Spatial ring-2 (#4: Δ+0.007)
    "neighbor_danger_r2",

    # Economic (Δ+0.002)
    "lbp_usd_parallel", "lbp_change_7d", "lbp_change_30d", "lbp_volatility_7d",

    # Actor novelty
    "unique_actors", "actor_pair_count",

    # Military/OSINT
    "siren_count",

    # ── NEW: Anomaly detection features (Priority 1) ──────────

    # Z-scores (how anomalous is today vs 30-day baseline?)
    "gdelt_hostility_zscore", "gdelt_event_count_zscore",
    "neighbor_danger_zscore", "lbp_zscore",
    "firms_zscore", "ntl_zscore", "siren_zscore",

    # Residuals (deviation from hex-specific median)
    "gdelt_hostility_residual", "neighbor_danger_residual",
    "lbp_residual",

    # Acceleration (is the rate of change itself changing?)
    "gdelt_hostility_accel", "neighbor_danger_accel",
    "lbp_accel",

    # Cross-feature anomaly composites
    "anomaly_count", "max_anomaly",

    # ── NEW: GKG emotional dimensions + SAR damage ────────────
    # Require gdelt_hex_daily.parquet (text_nlp.py) and sar_damage_hex_daily.parquet

    # GKG emotional dims — fear/anger/anxiety from GCAM + CRISISLEX crisis themes
    "gdelt_fear_score", "gdelt_anger_score", "gdelt_anxiety_score",
    "gdelt_crisislex_count", "gdelt_arabic_count",
    "gdelt_fear_zscore", "gdelt_anger_zscore", "gdelt_arabic_zscore",

    # SAR structural damage (PWTT Sentinel-1) — building damage signal
    "damage_mean", "damage_fraction", "damage_velocity_7d", "damage_zscore",
]

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")


# ── Focal Loss ────────────────────────────────────────────────

def focal_loss_objective(predt, dtrain, gamma=2.0):
    """Custom focal loss objective for XGBoost.

    Down-weights easy-to-classify examples (the massive number of true
    negatives in onset prediction), focuses learning on the hard cases
    near the decision boundary.

    gamma=0 → standard logistic loss
    gamma=2 → standard focal loss (Lin et al. 2017)
    """
    y = dtrain.get_label()
    p = expit(predt)

    # Focal weighting: hard examples get higher weight
    # For positives (y=1): weight = (1-p)^gamma  (high when model says "no" but truth is "yes")
    # For negatives (y=0): weight = p^gamma       (high when model says "yes" but truth is "no")
    focal_weight = np.where(y == 1, (1 - p) ** gamma, p ** gamma)

    grad = focal_weight * (p - y)
    hess = focal_weight * p * (1 - p)
    hess = np.maximum(hess, 1e-7)  # numerical stability

    return grad, hess


def focal_eval_aucpr(predt, dtrain):
    """Custom eval metric: AUC-PR (needed since focal loss uses raw logits)."""
    y = dtrain.get_label()
    p = expit(predt)
    return "aucpr", average_precision_score(y, p)


def train_onset():
    std_path = os.path.join(MODEL_DIR, "xgb_onset.ubj")
    focal_path = os.path.join(MODEL_DIR, "xgb_onset_focal.ubj")

    if os.path.exists(std_path) and os.path.exists(focal_path):
        print("Cache hit: both onset models exist")
        return

    data_path = os.path.join(os.path.dirname(__file__), "..",
                             "data", "processed", "onset_set.parquet")
    df = pd.read_parquet(data_path)

    features = [f for f in ONSET_FEATURES if f in df.columns]
    print(f"Onset features: {len(features)}/{len(ONSET_FEATURES)}")
    missing = set(ONSET_FEATURES) - set(features)
    if missing:
        print(f"  Missing: {missing}")

    train = df[df["date"] <= pd.Timestamp(TRAIN_CUTOFF)]
    test = df[df["date"] >= pd.Timestamp(TEST_START)]

    X_train, y_train = train[features].fillna(0), train["label"]
    X_test, y_test = test[features].fillna(0), test["label"]

    n_pos = max((y_train == 1).sum(), 1)
    n_neg = (y_train == 0).sum()
    scale = n_neg / n_pos
    print(f"  Train: {len(train):,} rows, {n_pos:,} pos (scale={scale:.0f})")
    print(f"  Test:  {len(test):,} rows, {(y_test==1).sum():,} pos")

    os.makedirs(MODEL_DIR, exist_ok=True)

    # ── Load Optuna-tuned hyperparams if available ────────────
    hp_path = os.path.join(MODEL_DIR, "best_hyperparams.json")
    tuned = {}
    if os.path.exists(hp_path):
        import json
        with open(hp_path) as f:
            tuned = json.load(f).get("onset", {})
        print(f"  Loaded Optuna params: max_depth={tuned.get('max_depth')}, "
              f"lr={tuned.get('learning_rate', 0):.4f}, "
              f"subsample={tuned.get('subsample', 0):.3f}")

    hp = {
        "max_depth": tuned.get("max_depth", 5),
        "learning_rate": tuned.get("learning_rate", 0.05),
        "subsample": tuned.get("subsample", 0.7),
        "colsample_bytree": tuned.get("colsample_bytree", 0.7),
        "min_child_weight": tuned.get("min_child_weight", 10),
        "gamma": tuned.get("gamma", 0),
        "reg_alpha": tuned.get("reg_alpha", 0),
        "reg_lambda": tuned.get("reg_lambda", 1),
    }

    # ── 1. Standard XGBoost (scale_pos_weight) ────────────────
    if not os.path.exists(std_path):
        print("\n  Training STANDARD onset model...")
        model_std = xgb.XGBClassifier(
            n_estimators=500, scale_pos_weight=scale,
            eval_metric="aucpr", early_stopping_rounds=30,
            random_state=RANDOM_SEED, **hp,
        )
        model_std.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=50)
        model_std.save_model(std_path)

        preds = model_std.predict_proba(X_test)[:, 1]
        aucpr = average_precision_score(y_test, preds)
        print(f"  Standard onset: AUC-PR={aucpr:.4f} (best iter: {model_std.best_iteration})")

    # ── 2. Focal Loss XGBoost ─────────────────────────────────
    if not os.path.exists(focal_path):
        print("\n  Training FOCAL LOSS onset model (gamma=2.0)...")
        w_train = train["sample_weight"].values if "sample_weight" in train.columns else None
        dtrain = xgb.DMatrix(X_train, label=y_train, weight=w_train)
        dtest = xgb.DMatrix(X_test, label=y_test)

        params = {
            "seed": RANDOM_SEED,
            "disable_default_eval_metric": True,
            **{k: v for k, v in hp.items() if k != "gamma"},  # focal has its own gamma
        }

        model_focal = xgb.train(
            params, dtrain, num_boost_round=500,
            obj=focal_loss_objective,
            custom_metric=focal_eval_aucpr,
            evals=[(dtest, "test")],
            early_stopping_rounds=30,
            verbose_eval=50,
        )
        model_focal.save_model(focal_path)

        preds_focal = expit(model_focal.predict(dtest))
        aucpr_focal = average_precision_score(y_test, preds_focal)
        print(f"  Focal onset: AUC-PR={aucpr_focal:.4f} "
              f"(best iter: {model_focal.best_iteration})")


if __name__ == "__main__":
    train_onset()
