"""
05_score_live.py — Live Scoring Engine
=======================================
Reads the most recent day of features from the enriched CSV,
runs XGBoost + tactical scoring, and upserts results to Supabase risk_scores.

Feature set matches 02_train_model.py (daily grain, v5).
Production model: models/xgb_sentinel.ubj (Standard XGBoost @ threshold 0.75).

Called:
  - Manually:  python backend/05_score_live.py
  - By cron:   APScheduler in main.py fires this every 15 minutes

Run from sentinel/ root:
    cd sentinel && python backend/05_score_live.py
"""

import os
import sys
import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.special import expit
from supabase import create_client
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from tactical_alert import score_hex

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Auto-pick richest available feature file (daily grain preferred)
for candidate in [
    "data/processed/acled_h3_gdelt_firms_weather.csv",
    "data/processed/acled_h3_gdelt_firms.csv",
    "data/processed/acled_h3_gdelt.csv",
    "data/processed/acled_h3.csv",
]:
    path = os.path.join(ROOT, candidate)
    if os.path.exists(path):
        FEATURE_PATH = path
        break
else:
    sys.exit("No processed feature file found. Run the pipeline first.")

MODEL_PATH = os.path.join(ROOT, "models", "xgb_sentinel.ubj")

# ── Feature columns — must match 02_train_model.py v5 (daily grain) ──────────
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
    # Temporal lags (yesterday / 2 days ago)
    "dangerous_lag1",
    "dangerous_lag2",
    "fatalities_lag1",
    "battle_lag1",
    "explosion_lag1",
]

GDELT_FEATURES = [
    "gdelt_event_count",
    "gdelt_avg_tone",
    "gdelt_min_goldstein",
    "gdelt_avg_goldstein",
    "gdelt_num_articles",
    "gdelt_hostility",
    "neighbor_gdelt_hostility_avg",
]

FIRMS_FEATURES = [
    "firms_hotspot_count",
    "firms_avg_frp",
    "firms_max_frp",
    "firms_spike",
    "neighbor_firms_spike_sum",
]

GDELT_CAMEO_FEATURES = [
    "gdelt_protest_count",
    "gdelt_threaten_count",
    "gdelt_assault_count",
    "gdelt_fight_count",
    "gdelt_cameo_conflict",
    "neighbor_gdelt_protest_avg",
]

WEATHER_FEATURES = [
    "temp_max",
    "temp_anomaly_30d",
    "precip_mm",
    "precip_spike",
]

# Strategic tier thresholds (Standard XGBoost, production @ 0.75)
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


def load_model(path: str):
    """
    Load production model. Tries XGBClassifier first (standard),
    falls back to xgb.Booster (focal loss). Returns (model, is_booster).
    """
    try:
        clf = xgb.XGBClassifier()
        clf.load_model(path)
        return clf, False
    except Exception:
        booster = xgb.Booster()
        booster.load_model(path)
        return booster, True


def predict_proba(model, is_booster: bool, X: pd.DataFrame) -> np.ndarray:
    if is_booster:
        # Align columns to exactly what the model was trained on, filling gaps with 0
        model_features = model.feature_names
        if model_features:
            for col in model_features:
                if col not in X.columns:
                    X[col] = 0
            X = X[model_features]
        raw = model.predict(xgb.DMatrix(X))
        return expit(raw)   # focal booster outputs raw logits
    return model.predict_proba(X)[:, 1]


def run_scoring():
    if not SUPABASE_URL or not SUPABASE_KEY:
        sys.exit("SUPABASE_URL and SUPABASE_KEY not set in backend/.env")

    print(f"Loading features from {FEATURE_PATH}...")
    df = pd.read_csv(FEATURE_PATH)
    date_col = next((c for c in ["date", "event_date", "week"] if c in df.columns), None)
    if date_col is None:
        sys.exit("No date column found in feature file (expected: date, event_date, or week)")
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(["h3_id", date_col])

    # Most recent record per hex
    latest = df.groupby("h3_id").last().reset_index()
    print(f"  {len(latest):,} hexes to score (latest {date_col} per hex)")

    # Build feature matrix — only use columns present in this file
    features = BASE_FEATURES.copy()
    for col in GDELT_FEATURES + FIRMS_FEATURES + GDELT_CAMEO_FEATURES + WEATHER_FEATURES:
        if col in latest.columns:
            features.append(col)
    features = [f for f in features if f in latest.columns]

    X = latest[features].fillna(0)

    print(f"Loading model from {MODEL_PATH}...")
    model, is_booster = load_model(MODEL_PATH)
    print(f"  Model type: {'Booster/focal' if is_booster else 'XGBClassifier/standard'}")

    print("Running XGBoost inference...")
    proba = predict_proba(model, is_booster, X)
    latest["strategic_score"] = proba
    latest["strategic_tier"]  = [strategic_tier(s) for s in proba]

    print("Running tactical scoring...")
    records = []
    for _, row in latest.iterrows():
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
            # daily column names → tactical_alert parameter names
            event_velocity=row.get("dangerous_velocity", row.get("event_velocity", 1.0)),
            neighbor_event_avg=row.get("neighbor_danger_avg", row.get("neighbor_event_avg", 0)),
            neighbor_fatal_sum=row.get("neighbor_fatal_sum", 0),
            strategic_score=float(row["strategic_score"]),
        )
        records.append({
            "h3_id":             row["h3_id"],
            "strategic_score":   round(float(row["strategic_score"]), 4),
            "strategic_tier":    row["strategic_tier"],
            "tactical_score":    alert.score,
            "tactical_tier":     alert.risk_level,
            "should_alert":      bool(alert.should_alert),
            "tactical_triggers": " | ".join(alert.triggers),
            "alert_text":        None,
        })

    print(f"Upserting {len(records):,} rows to risk_scores...")
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    BATCH = 500
    for i in range(0, len(records), BATCH):
        client.table("risk_scores").upsert(records[i : i + BATCH]).execute()

    danger_count = sum(1 for r in records if r["tactical_tier"] == "DANGER")
    print(f"  Done. DANGER hexes this run: {danger_count}")

    # Gemini alert text for DANGER hexes
    if danger_count > 0:
        try:
            from alerting_agent import generate_alert
            danger_ids = {r["h3_id"] for r in records if r["tactical_tier"] == "DANGER"}
            print(f"Generating Gemini alerts for {len(danger_ids)} DANGER hexes...")
            for _, row in latest[latest["h3_id"].isin(danger_ids)].iterrows():
                alert_text = generate_alert(row.to_dict())
                if alert_text:
                    client.table("risk_scores").update(
                        {"alert_text": alert_text}
                    ).eq("h3_id", row["h3_id"]).execute()
        except Exception as e:
            print(f"  Warning: Gemini alert generation failed — {e}")

    return records


if __name__ == "__main__":
    run_scoring()
    print("Scoring complete.")
