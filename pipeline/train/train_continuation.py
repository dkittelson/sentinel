"""Train continuation model: predict escalation in active hexes."""
import pandas as pd
import numpy as np
import os
import sys
import xgboost as xgb

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ml.config import TRAIN_CUTOFF, TEST_START, RANDOM_SEED

# Continuation features — use everything including violence history.
CONT_FEATURES = [
    # Violence history (primary continuation signal)
    "event_count", "dangerous_count", "total_fatalities", "max_fatalities",
    "battle_count", "explosion_count", "vac_count", "riot_count",
    # Rolling windows (multi-timescale dynamics)
    "dangerous_roll3d", "dangerous_roll7d", "dangerous_roll14d",
    "fatalities_roll3d", "fatalities_roll7d", "fatalities_roll14d",
    "event_roll3d", "event_roll7d", "event_roll14d",
    # Velocity (is violence accelerating?)
    "dangerous_delta", "fatality_delta",
    "dangerous_velocity", "fatality_velocity",
    # Actor dynamics
    "unique_actors", "actor_pair_count",
    "actor_pair_delta", "actor_pair_velocity",
    # Spatial lags
    "neighbor_danger_avg", "neighbor_fatal_sum",
    # Ring-2 spatial
    "neighbor_danger_r2",
    # Spatial FIRMS + NTL neighbors
    "neighbor_firms_avg", "neighbor_ntl_avg",
    # Nighttime lights (infrastructure destruction in progress)
    "ntl_mean", "ntl_delta_7d", "ntl_anomaly_30d",
    # Military/OSINT
    "siren_count",
    # Calendar
    "is_ramadan", "is_jerusalem_day", "is_election_window",
    # GDELT
    "gdelt_event_count", "gdelt_avg_tone", "gdelt_min_goldstein",
    "gdelt_avg_goldstein", "gdelt_num_articles", "gdelt_hostility",
    "neighbor_gdelt_hostility_avg",
    # FIRMS
    "firms_hotspot_count", "firms_avg_frp", "firms_max_frp", "firms_spike",
    "neighbor_firms_spike_sum",
    # Weather
    "temp_max", "temp_anomaly_30d", "precip_mm", "precip_spike",
    # GDELT velocity/dynamics
    "gdelt_hostility_roll3d", "gdelt_hostility_roll7d", "gdelt_hostility_velocity",
    "gdelt_event_roll3d", "gdelt_event_roll7d", "gdelt_event_velocity",
    "gdelt_tone_delta",
    # Interactions (Δ+0.006)
    "hostility_x_neighbor_danger", "ntl_drop_x_fire",
    "economic_stress", "hostility_x_sirens",
    # Spatial gradient + regime (Δ+0.004)
    "spatial_gradient", "post_oct7",
    # Food security (Δ+0.006)
    "ipc_phase_lb", "ipc_phase_sy", "ipc_phase_max", "ipc_crisis_flag",
    # Google Trends (Δ+0.006 for continuation)
    "gtrends_callup_order_il", "gtrends_reserves_il", "gtrends_home_front_il",
    "gtrends_shelter_he_il", "gtrends_shelter_ar_lb", "gtrends_war_ar_lb",
    "gtrends_shelling_ar_lb", "gtrends_shelter_ar_sy",
    "gtrends_war_ar_sy", "gtrends_shelling_ar_sy",
    # Population/infrastructure (Δ+0.024)
    "population_best", "worldpop_population",
    "hospital_count", "school_count",

    # ── NEW: GKG emotional dimensions ────────────────────────
    "gdelt_fear_score", "gdelt_anger_score", "gdelt_anxiety_score",
    "gdelt_crisislex_count", "gdelt_arabic_count",

    # ── NEW: SAR structural damage (PWTT Sentinel-1) ─────────
    "damage_mean", "damage_fraction", "damage_velocity_7d",

    # ── REMOVED (hurt continuation per ablation) ─────────────
    # calendar:  Δ-0.013 (noise for both models)
    # economic:  Δ-0.008 (LBP rate hurts continuation)
]

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "xgb_continuation.ubj")


def train_continuation():
    if os.path.exists(MODEL_PATH):
        print("Cache hit: continuation model exists")
        return

    data_path = os.path.join(os.path.dirname(__file__), "..",
                             "data", "processed", "continuation_set.parquet")
    df = pd.read_parquet(data_path)

    features = [f for f in CONT_FEATURES if f in df.columns]
    print(f"Continuation features: {len(features)}/{len(CONT_FEATURES)}")

    train = df[df["date"] <= pd.Timestamp(TRAIN_CUTOFF)]
    test = df[df["date"] >= pd.Timestamp(TEST_START)]

    X_train = train[features].fillna(0).values.astype(np.float32)
    y_train = train["label"].values
    X_test = test[features].fillna(0).values.astype(np.float32)
    y_test = test["label"].values

    n_pos = max((y_train == 1).sum(), 1)
    n_neg = (y_train == 0).sum()
    scale = n_neg / n_pos
    print(f"  Train: {len(train):,} rows, {n_pos:,} positives (scale={scale:.1f})")
    print(f"  Test:  {len(test):,} rows, {(y_test==1).sum():,} positives")

    # Load Optuna-tuned hyperparams if available
    hp_path = os.path.join(MODEL_PATH.replace("xgb_continuation.ubj", ""), "best_hyperparams.json")
    tuned = {}
    if os.path.exists(hp_path):
        import json
        with open(hp_path) as f:
            tuned = json.load(f).get("continuation", {})
        print(f"  Loaded Optuna params: max_depth={tuned.get('max_depth')}")

    model = xgb.XGBClassifier(
        n_estimators=500,
        max_depth=tuned.get("max_depth", 5),
        learning_rate=tuned.get("learning_rate", 0.05),
        scale_pos_weight=scale,
        subsample=tuned.get("subsample", 0.7),
        colsample_bytree=tuned.get("colsample_bytree", 0.7),
        min_child_weight=tuned.get("min_child_weight", 10),
        gamma=tuned.get("gamma", 0),
        reg_alpha=tuned.get("reg_alpha", 0),
        reg_lambda=tuned.get("reg_lambda", 1),
        eval_metric="aucpr",
        early_stopping_rounds=30,
        random_state=RANDOM_SEED,
    )
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=50)

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    model.save_model(MODEL_PATH)
    print(f"Continuation model saved (best iter: {model.best_iteration})")


if __name__ == "__main__":
    train_continuation()
