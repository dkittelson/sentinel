# ── Feature catalog (April 2026) ──────────────────────────────
#
# Authoritative feature lists are in the training scripts:
#   - pipeline/train/train_onset.py → ONSET_FEATURES (39 features)
#   - pipeline/train/train_continuation.py → CONT_FEATURES (83 features)
#
# This file provides the grouped catalog for reference.
# At runtime, training scripts filter to features that exist in the data.

# ── Onset Features (39 total, ranked by ablation impact) ──────

# #1: Z-scores — anomaly detection (Δ+0.066 if removed)
ZSCORE_FEATURES = [
    "gdelt_hostility_zscore", "gdelt_event_count_zscore",
    "neighbor_danger_zscore", "lbp_zscore",
    "firms_zscore", "ntl_zscore", "siren_zscore",
]

# #2: Population/infrastructure (Δ+0.048)
POPULATION_FEATURES = [
    "population_best", "worldpop_population",
    "hospital_count", "school_count",
]

# #3-4: Spatial lags (Δ+0.012 ring-1, Δ+0.021 ring-2)
SPATIAL_FEATURES = [
    "neighbor_danger_avg", "neighbor_fatal_sum",
    "neighbor_gdelt_hostility_avg", "neighbor_firms_avg",
    "spatial_gradient",
    "neighbor_danger_r2",
]

# #5: GDELT dynamics (Δ+0.016)
GDELT_DYNAMICS = [
    "gdelt_hostility_roll3d", "gdelt_hostility_roll7d", "gdelt_hostility_velocity",
    "gdelt_event_roll3d", "gdelt_event_roll7d", "gdelt_event_velocity",
    "gdelt_tone_delta",
]

# #6: Residuals — deviation from hex baseline (Δ+0.015)
RESIDUAL_FEATURES = [
    "gdelt_hostility_residual", "neighbor_danger_residual", "lbp_residual",
]

# #7: Acceleration — second-order dynamics (Δ+0.016)
ACCELERATION_FEATURES = [
    "gdelt_hostility_accel", "neighbor_danger_accel", "lbp_accel",
]

# #8: Anomaly composites (Δ+0.014)
COMPOSITE_FEATURES = [
    "anomaly_count", "max_anomaly",
]

# #9: Economic (Δ+0.013)
ECONOMIC_FEATURES = [
    "lbp_usd_parallel", "lbp_change_7d", "lbp_change_30d", "lbp_volatility_7d",
]

# #10: Actor/OSINT (Δ+0.013)
ACTOR_FEATURES = [
    "unique_actors", "actor_pair_count", "siren_count",
]

# ── Continuation-Only Features ────────────────────────────────
# These help continuation but hurt onset (per ablation)

CONFLICT_ROLLING = [
    "dangerous_roll3d", "dangerous_roll7d", "dangerous_roll14d",
    "fatalities_roll3d", "fatalities_roll7d", "fatalities_roll14d",
    "event_roll3d", "event_roll7d", "event_roll14d",
]

CONFLICT_BASE = [
    "event_count", "dangerous_count", "total_fatalities", "max_fatalities",
    "battle_count", "explosion_count", "vac_count", "riot_count",
]

CONFLICT_VELOCITY = [
    "dangerous_delta", "fatality_delta",
    "dangerous_velocity", "fatality_velocity",
    "actor_pair_delta", "actor_pair_velocity",
]

NTL_FEATURES = [
    "ntl_mean", "ntl_delta_7d", "ntl_anomaly_30d",
]

FIRMS_FEATURES = [
    "firms_hotspot_count", "firms_avg_frp", "firms_max_frp", "firms_spike",
    "neighbor_firms_spike_sum",
]

WEATHER_FEATURES = [
    "temp_max", "temp_anomaly_30d", "precip_mm", "precip_spike",
]

# ── Removed Features (noise per ablation) ─────────────────────
# Calendar: Δ-0.009 onset, Δ-0.013 continuation (HURTS BOTH)
# Raw GDELT base: Δ-0.002 (dynamics already capture the signal)
# Interactions: Δ-0.002 (XGBoost learns these automatically)

# ── Combined ──────────────────────────────────────────────────

ONSET_FEATURES_ALL = (
    ZSCORE_FEATURES + POPULATION_FEATURES + SPATIAL_FEATURES
    + GDELT_DYNAMICS + RESIDUAL_FEATURES + ACCELERATION_FEATURES
    + COMPOSITE_FEATURES + ECONOMIC_FEATURES + ACTOR_FEATURES
)

CONTINUATION_FEATURES_ALL = (
    CONFLICT_BASE + CONFLICT_ROLLING + CONFLICT_VELOCITY
    + SPATIAL_FEATURES + NTL_FEATURES + GDELT_DYNAMICS
    + FIRMS_FEATURES + WEATHER_FEATURES
    + POPULATION_FEATURES + ACTOR_FEATURES
    + ZSCORE_FEATURES + RESIDUAL_FEATURES + ACCELERATION_FEATURES
    + COMPOSITE_FEATURES + ECONOMIC_FEATURES
)


def get_available_features(df):
    """Filter ALL features to columns that exist in the dataframe."""
    all_feats = list(set(ONSET_FEATURES_ALL + CONTINUATION_FEATURES_ALL))
    return [f for f in all_feats if f in df.columns]
