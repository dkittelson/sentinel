"""
backtest_score.py — Historical Backtesting Engine
===================================================
Scores all hexes for a given historical date using the production XGBoost model.
Returns JSON-ready list of hex scores (no Supabase writes).

Used by GET /hexes/backtest?date=YYYY-MM-DD to power the demo time-slider.
"""

import os
import sys
import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.special import expit
from functools import lru_cache

sys.path.insert(0, os.path.dirname(__file__))
from tactical_alert import score_hex

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# ── Feature columns (must match 02_train_model.py / 05_score_live.py) ────────
BASE_FEATURES = [
    "event_count", "dangerous_count", "total_fatalities", "max_fatalities",
    "battle_count", "explosion_count", "vac_count", "riot_count",
    "population_best", "unique_actors",
    "dangerous_roll3d", "dangerous_roll7d", "dangerous_roll14d",
    "fatalities_roll3d", "fatalities_roll7d", "fatalities_roll14d",
    "event_roll3d", "event_roll7d", "event_roll14d",
    "dangerous_delta", "fatality_delta", "dangerous_velocity", "fatality_velocity",
    "neighbor_danger_avg", "neighbor_fatal_sum",
    "actor_pair_count", "actor_pair_delta", "actor_pair_velocity",
    "dangerous_lag1", "dangerous_lag2", "fatalities_lag1", "battle_lag1", "explosion_lag1",
]

GDELT_FEATURES = [
    "gdelt_event_count", "gdelt_avg_tone", "gdelt_min_goldstein",
    "gdelt_avg_goldstein", "gdelt_num_articles", "gdelt_hostility",
    "neighbor_gdelt_hostility_avg",
]

FIRMS_FEATURES = [
    "firms_hotspot_count", "firms_avg_frp", "firms_max_frp", "firms_spike",
    "neighbor_firms_spike_sum",
]

# Strategic tier thresholds (match 05_score_live.py)
STRATEGIC_TIERS = [
    (0.70, "red"),
    (0.45, "orange"),
    (0.25, "yellow"),
    (0.0,  "green"),
]


def strategic_tier(score: float) -> str:
    for threshold, tier in STRATEGIC_TIERS:
        if score >= threshold:
            return tier
    return "green"


# ── Cached data loading ──────────────────────────────────────────────────────

_df_cache = None
_model_cache = None


def _load_data():
    """Load and cache the full feature CSV (only once per process). Compute lag features."""
    global _df_cache
    if _df_cache is not None:
        return _df_cache

    for candidate in [
        "data/processed/acled_h3_gdelt_firms.csv",
        "data/processed/acled_h3_gdelt.csv",
        "data/processed/acled_h3.csv",
    ]:
        path = os.path.join(ROOT, candidate)
        if os.path.exists(path):
            print(f"[backtest] Loading {candidate}...")
            _df_cache = pd.read_csv(path)
            _df_cache["event_date"] = pd.to_datetime(_df_cache["event_date"])
            _df_cache = _df_cache.sort_values(["h3_id", "event_date"])

            # Compute temporal lag features (same as 02_train_model.py)
            print("[backtest] Computing temporal lag features...")
            for col, shift_n, new_col in [
                ("dangerous_count",  1, "dangerous_lag1"),
                ("dangerous_count",  2, "dangerous_lag2"),
                ("total_fatalities", 1, "fatalities_lag1"),
                ("battle_count",     1, "battle_lag1"),
                ("explosion_count",  1, "explosion_lag1"),
            ]:
                if col in _df_cache.columns:
                    _df_cache[new_col] = _df_cache.groupby("h3_id")[col].shift(shift_n).fillna(0)

            print(f"[backtest] {len(_df_cache):,} rows loaded, "
                  f"{_df_cache['event_date'].min().date()} to {_df_cache['event_date'].max().date()}")
            return _df_cache

    raise FileNotFoundError("No processed feature CSV found")


def _load_model():
    """Load and cache the production XGBoost model."""
    global _model_cache
    if _model_cache is not None:
        return _model_cache

    model_path = os.path.join(ROOT, "models", "xgb_sentinel.ubj")
    try:
        clf = xgb.XGBClassifier()
        clf.load_model(model_path)
        _model_cache = (clf, False)
    except Exception:
        booster = xgb.Booster()
        booster.load_model(model_path)
        _model_cache = (booster, True)

    print(f"[backtest] Model loaded: {'Booster' if _model_cache[1] else 'Classifier'}")
    return _model_cache


def predict_proba(model, is_booster: bool, X: pd.DataFrame) -> np.ndarray:
    if is_booster:
        model_features = model.feature_names
        if model_features:
            for col in model_features:
                if col not in X.columns:
                    X[col] = 0
            X = X[model_features]
        raw = model.predict(xgb.DMatrix(X))
        return expit(raw)
    # XGBClassifier — align to model's expected features
    model_features = model.get_booster().feature_names
    if model_features:
        for col in model_features:
            if col not in X.columns:
                X[col] = 0
        X = X[model_features]
    return model.predict_proba(X)[:, 1]


def score_date(date_str: str) -> list[dict]:
    """
    Score all hexes for a given date. Returns list of dicts ready for JSON.
    """
    df = _load_data()
    model, is_booster = _load_model()

    target_date = pd.Timestamp(date_str)
    day_data = df[df["event_date"] == target_date].copy()

    if day_data.empty:
        return []

    # Build feature matrix
    features = BASE_FEATURES.copy()
    for col in GDELT_FEATURES + FIRMS_FEATURES:
        if col in day_data.columns:
            features.append(col)
    features = [f for f in features if f in day_data.columns]

    X = day_data[features].fillna(0).copy()

    # Run XGBoost
    proba = predict_proba(model, is_booster, X)
    day_data["strategic_score"] = proba
    day_data["strategic_tier"] = [strategic_tier(s) for s in proba]

    # Run tactical scoring + build response
    records = []
    for _, row in day_data.iterrows():
        alert = score_hex(
            h3_id=row["h3_id"],
            firms_hotspot_count=row.get("firms_hotspot_count", 0),
            firms_avg_frp=row.get("firms_avg_frp", 0),
            firms_max_frp=row.get("firms_max_frp", 0),
            firms_spike=int(row.get("firms_spike", 0)),
            gdelt_hostility=row.get("gdelt_hostility", 0),
            gdelt_min_goldstein=row.get("gdelt_min_goldstein", 0),
            gdelt_avg_tone=row.get("gdelt_avg_tone", 0),
            gdelt_event_count=row.get("gdelt_event_count", 0),
            event_velocity=row.get("dangerous_velocity", 1.0),
            neighbor_event_avg=row.get("neighbor_danger_avg", 0),
            neighbor_fatal_sum=row.get("neighbor_fatal_sum", 0),
            strategic_score=float(row["strategic_score"]),
        )
        records.append({
            "h3_id":           row["h3_id"],
            "strategic_score": round(float(row["strategic_score"]), 4),
            "strategic_tier":  row["strategic_tier"],
            "tactical_score":  round(alert.score, 4),
            "tactical_tier":   alert.risk_level,
            "should_alert":    bool(alert.should_alert),
            "tactical_triggers": " | ".join(alert.triggers),
            "scored_at":       date_str,
        })

    return records


def get_date_range() -> dict:
    """Return the min/max dates available for backtesting."""
    df = _load_data()
    return {
        "min_date": str(df["event_date"].min().date()),
        "max_date": str(df["event_date"].max().date()),
    }
