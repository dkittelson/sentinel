"""
05_score_live.py — Live Scoring Engine
=======================================
Reads the most recent week of features from the enriched CSV,
runs XGBoost + tactical scoring, and upserts results to Supabase risk_scores.

Called:
  - Manually:  python backend/05_score_live.py
  - By cron:   APScheduler in main.py fires this every 15 minutes

Run from sentinel/ root:
    cd sentinel && python backend/05_score_live.py
"""

import os
import sys
import pandas as pd
import numpy as np
import xgboost as xgb
from supabase import create_client
from dotenv import load_dotenv

# Tactical alert layer lives in backend/
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from tactical_alert import score_hex

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Auto-pick richest available feature file
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

# ── Feature columns (must match 02_train_model.py) ────────────────────────────
BASE_FEATURES = [
    "event_count", "total_fatalities", "max_fatalities",
    "battle_count", "explosion_count", "vac_count",
    "population_best", "unique_actors",
    "event_count_roll2w", "fatalities_roll2w",
    "event_count_roll4w", "fatalities_roll4w",
    "event_count_delta", "fatality_delta",
    "event_velocity", "fatality_velocity",
    "neighbor_event_avg", "neighbor_fatal_sum",
    "actor_pair_count", "actor_pair_delta", "actor_pair_velocity",
]
GDELT_FEATURES = [
    "gdelt_event_count", "gdelt_avg_tone", "gdelt_min_goldstein",
    "gdelt_avg_goldstein", "gdelt_num_articles", "gdelt_hostility",
    "neighbor_gdelt_hostility_avg",
]
FIRMS_FEATURES = [
    "firms_hotspot_count", "firms_avg_frp", "firms_max_frp", "firms_spike",
]
WEATHER_FEATURES = [
    "weather_temp_max", "weather_temp_mean", "weather_temp_anomaly",
    "weather_precip_sum", "weather_precip_anomaly", "weather_drought_days",
]

STRATEGIC_TIERS = [
    (0.7, "red"),
    (0.5, "orange"),
    (0.3, "yellow"),
    (0.0, "green"),
]


def strategic_tier(score: float) -> str:
    for threshold, tier in STRATEGIC_TIERS:
        if score >= threshold:
            return tier
    return "green"


def run_scoring():
    if not SUPABASE_URL or not SUPABASE_KEY:
        sys.exit("SUPABASE_URL and SUPABASE_KEY not set in backend/.env")

    print(f"Loading features from {FEATURE_PATH}...")
    df = pd.read_csv(FEATURE_PATH, parse_dates=["week"])
    df = df.sort_values(["h3_id", "week"])

    # Keep only the most recent week per hex
    latest = df.groupby("h3_id").last().reset_index()
    print(f"  {len(latest):,} hexes to score (latest week per hex)")

    # Build feature matrix (only columns present in this file)
    features = BASE_FEATURES.copy()
    for col in GDELT_FEATURES + FIRMS_FEATURES + WEATHER_FEATURES:
        if col in latest.columns:
            features.append(col)

    X = latest[features].fillna(0)

    print(f"Loading model from {MODEL_PATH}...")
    model = xgb.XGBClassifier()
    model.load_model(MODEL_PATH)

    print("Running XGBoost inference...")
    strategic_scores = model.predict_proba(X)[:, 1]
    latest["strategic_score"] = strategic_scores
    latest["strategic_tier"] = [strategic_tier(s) for s in strategic_scores]

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
            event_velocity=row.get("event_velocity", 1.0),
            neighbor_event_avg=row.get("neighbor_event_avg", 0),
            neighbor_fatal_sum=row.get("neighbor_fatal_sum", 0),
            strategic_score=float(row["strategic_score"]),
        )
        records.append({
            "h3_id": row["h3_id"],
            "strategic_score": round(float(row["strategic_score"]), 4),
            "strategic_tier": row["strategic_tier"],
            "tactical_score": alert.score,
            "tactical_tier": alert.risk_level,
            "should_alert": bool(alert.should_alert),
            "tactical_triggers": " | ".join(alert.triggers),
            "alert_text": None,   # filled by alerting_agent if DANGER
        })

    print(f"Upserting {len(records):,} rows to risk_scores...")
    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    BATCH = 500
    for i in range(0, len(records), BATCH):
        batch = records[i : i + BATCH]
        client.table("risk_scores").upsert(batch).execute()

    danger_count = sum(1 for r in records if r["tactical_tier"] == "DANGER")
    print(f"  Done. DANGER hexes this run: {danger_count}")

    # Trigger Gemini alert generation for DANGER hexes that have no alert_text yet
    if danger_count > 0:
        try:
            from alerting_agent import generate_alert
            print("Generating Gemini alert text for DANGER hexes...")
            for _, row in latest[latest["h3_id"].isin(
                [r["h3_id"] for r in records if r["tactical_tier"] == "DANGER"]
            )].iterrows():
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
