import os

# ── Paths ──────────────────────────────────────────────────────
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODEL_DIR = os.path.join(ROOT, "models")

# ── Reproducibility ───────────────────────────────────────────
RANDOM_SEED = 42

# ── Hex Grid ──────────────────────────────────────────────────
H3_RESOLUTION = 6

# ── Timeline ──────────────────────────────────────────────────
START_DATE = "2020-01-01"
END_DATE   = "2024-12-10"

# ── Label ─────────────────────────────────────────────────────
LABEL_HORIZON_HOURS = 72

# ── Alert Thresholds ──────────────────────────────────────────
STRATEGIC_TIERS = [
    (0.70, "red"),
    (0.63, "orange"),
    (0.54, "yellow"),
    (0.0,  "green"),
]

# ── Dangerous Event Types ─────────────────────────────────────
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

# ── Data Freshness Contract (source → lag in days) ────────────
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