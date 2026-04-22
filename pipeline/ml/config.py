"""Sentinel ML Pipeline — Centralized Configuration

Architecture: XGBoost (onset, 39 features) + GRU (continuation, 83 features)
Performance: Onset AUC-PR 0.246, Continuation AUC-PR 0.739
Last updated: April 2026
"""
import os

# ── Paths ──────────────────────────────────────────────────────
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODEL_DIR = os.path.join(ROOT, "models")

# ── Reproducibility ───────────────────────────────────────────
RANDOM_SEED = 42

# ── Hex Grid ──────────────────────────────────────────────────
H3_RESOLUTION = 6               # ~36 km² per hex, ~6.8 km edge

# ── Timeline ──────────────────────────────────────────────────
START_DATE = "2020-01-01"
END_DATE   = "2024-12-10"

# ── Label ─────────────────────────────────────────────────────
LABEL_HORIZON_DAYS = 7          # predict conflict in next 7 days

# ── Temporal Split ────────────────────────────────────────────
# Gap must be >= max_rolling_window(14) + label_horizon(7) = 21 days
# This prevents rolling-window feature leakage across train/test boundary
TEMPORAL_GAP_DAYS  = 21
TRAIN_CUTOFF       = "2024-06-10"   # last train date
TEST_START         = "2024-07-01"   # first test date

# ── Alert Thresholds ──────────────────────────────────────────
# NOTE: These were set for v1 uncalibrated scores. They need recalibration
# for v2 dual-model architecture (XGBoost onset + GRU continuation).
STRATEGIC_TIERS = [
    (0.70, "red"),
    (0.63, "orange"),
    (0.54, "yellow"),
    (0.0,  "green"),
]

# ── Dangerous Event Types (ACLED classification) ─────────────
DANGEROUS_TYPES = {
    "Battles",
    "Explosions/Remote violence",
    "Violence against civilians",
    "Riots",
}

DANGEROUS_PROTEST_SUBS = {
    "Excessive force against protesters",
    "Protest with intervention",
    "Violent demonstration",
}

# ── Publication Lags (enforced in split_data.py) ──────────────
# These shift features FORWARD by N days to simulate real-time availability.
# At scoring time t, ACLED data is only available through t-3.
# Without this enforcement, the model trains on data it wouldn't have
# in production, inflating metrics by up to 27% (verified by ablation).
PUB_LAGS = {
    "acled": 3,     # ACLED events arrive ~3 days late
    "gdelt": 1,     # GDELT ~1 day
    "firms": 0,     # FIRMS near-real-time (3h lag, negligible for daily)
    "weather": 0,   # weather near-real-time
}

# ── GRU / Sequence Model ─────────────────────────────────────
GRU_SEQ_LEN    = 14   # days of lookback — matches max rolling window used as features
GRU_HIDDEN_DIM = 64
GRU_LAYERS     = 2
GRU_DROPOUT    = 0.2
GRU_BATCH_SIZE = 2048
GRU_EPOCHS     = 50
GRU_LR         = 1e-3

# ── Anomaly Detection ─────────────────────────────────────────
# Z-scores ask "how unusual is today vs this hex's recent baseline?"
ZSCORE_WINDOW      = 30   # rolling days for mean/std baseline
ZSCORE_MIN_PERIODS = 7    # minimum rows before z-score is computed
ZSCORE_CLIP        = 10   # cap at ±10σ to suppress outlier influence
ANOMALY_THRESHOLD  = 2.0  # σ above which a reading is "anomalous"

# ── Recency Weighting ─────────────────────────────────────────
# Conflict dynamics shifted post-Oct-7 2023 (regime change point).
# Exponential decay weights recent data higher.
RECENCY_HALFLIFE_DAYS = 365   # half-life for sample_weight decay
RECENCY_FLOOR         = 0.1   # minimum weight (pre-2021 data still counts 10%)
REGIME_CHANGE_DATE    = "2023-10-07"

# ── Full Data Freshness Contract (source → lag in days) ───────
# Reference for all known sources — not all are enforced in pipeline
PUBLICATION_LAGS = {
    "acled":            3,
    "gdelt":            1,
    "firms":            0.125,
    "weather":          0.25,
    "black_marble":     1,
    "sentinel1":        3,
    "worldpop":         365,
    "ucdp_candidate":   30,
    "iom_dtm":          30,
    "wfp":              60,
    "calendar":         0,
    "opensky":          0,
    "telegram":         0,
    "ioda":             0,
    "ooni":             0,
    "wikipedia":        1,
    "google_trends":    2,
    "vdem":             365,
    "travel_advisory":  0,
    "sipri":            365,
    "cloudflare":       0,
}
