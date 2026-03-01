"""
Step 1: ACLED Data Preprocessing + H3 Binning
Ingests raw ACLED CSV, cleans it, and aggregates events into H3 hexagonal grid cells.
Output: data/processed/acled_h3.csv
"""

import pandas as pd
import h3
import numpy as np
from tqdm import tqdm

# ── Config ────────────────────────────────────────────────────────────────────
RAW_PATH = "data/raw/ACLED Data_2026-03-01.csv"
OUT_PATH  = "data/processed/acled_h3.csv"

# H3 resolution 6 ≈ ~36 km² hexagons — coarse enough to aggregate signal,
# fine enough to be spatially meaningful for civilian warnings.
H3_RESOLUTION = 6

# Only keep high-precision coordinates (1 = exact location, 2 = town-level)
GEO_PRECISION_MAX = 2

# Event types that represent actual violence (drop protests, riots, etc.)
VIOLENT_EVENTS = {
    "Battles",
    "Explosions/Remote violence",
    "Violence against civilians",
    "Strategic developments",  # includes abductions, base activity
}

# ── Load ──────────────────────────────────────────────────────────────────────
print(f"Loading {RAW_PATH}...")
df = pd.read_csv(RAW_PATH, low_memory=False)
print(f"  Raw rows: {len(df):,}")

# ── Clean ─────────────────────────────────────────────────────────────────────
# Parse date
df["event_date"] = pd.to_datetime(df["event_date"], dayfirst=True, errors="coerce")
df = df.dropna(subset=["event_date", "latitude", "longitude"])

# Drop low-precision coordinates
df = df[df["geo_precision"] <= GEO_PRECISION_MAX]

# Keep only violent event types
df = df[df["event_type"].isin(VIOLENT_EVENTS)]

# Ensure numeric fatalities
df["fatalities"] = pd.to_numeric(df["fatalities"], errors="coerce").fillna(0)
df["population_best"] = pd.to_numeric(df["population_best"], errors="coerce").fillna(0)

print(f"  After cleaning: {len(df):,} rows")

# ── H3 Binning ────────────────────────────────────────────────────────────────
print(f"Assigning H3 resolution-{H3_RESOLUTION} hex IDs...")

df["h3_id"] = df.apply(
    lambda row: h3.latlng_to_cell(row["latitude"], row["longitude"], H3_RESOLUTION),
    axis=1
)

# ── Temporal Windowing ────────────────────────────────────────────────────────
# Aggregate into weekly bins per hex — this is the unit the ML model trains on
df["week"] = df["event_date"].dt.to_period("W").dt.start_time

# ── Aggregate Features per (h3_id, week) ─────────────────────────────────────
print("Aggregating features per hex-week...")

agg = df.groupby(["h3_id", "week"]).agg(
    event_count       = ("event_type", "count"),
    total_fatalities  = ("fatalities", "sum"),
    max_fatalities    = ("fatalities", "max"),
    battle_count      = ("event_type", lambda x: (x == "Battles").sum()),
    explosion_count   = ("event_type", lambda x: (x == "Explosions/Remote violence").sum()),
    vac_count         = ("event_type", lambda x: (x == "Violence against civilians").sum()),
    population_best   = ("population_best", "max"),  # static per location
    unique_actors     = ("actor1", "nunique"),
).reset_index()

# ── Rolling Features (per hex, sorted by time) ───────────────────────────────
print("Computing rolling features...")

agg = agg.sort_values(["h3_id", "week"])

for window in [2, 4]:  # 2-week and 4-week rolling averages
    agg[f"event_count_roll{window}w"] = (
        agg.groupby("h3_id")["event_count"]
        .transform(lambda x: x.rolling(window, min_periods=1).mean())
    )
    agg[f"fatalities_roll{window}w"] = (
        agg.groupby("h3_id")["total_fatalities"]
        .transform(lambda x: x.rolling(window, min_periods=1).mean())
    )

# ── Label: Escalation in Next Week ───────────────────────────────────────────
# Binary label: did event_count INCREASE next week in this hex?
# This is what XGBoost will predict.
print("Generating escalation labels...")

agg["next_week_events"] = (
    agg.groupby("h3_id")["event_count"].shift(-1)
)
agg["label_escalation"] = (
    (agg["next_week_events"] > agg["event_count"]).astype(int)
)

# Drop the last week per hex (no label available)
agg = agg.dropna(subset=["next_week_events"])

# ── Save ──────────────────────────────────────────────────────────────────────
agg.to_csv(OUT_PATH, index=False)
print(f"\nSaved {len(agg):,} hex-week rows to {OUT_PATH}")
print(f"Unique hexes: {agg['h3_id'].nunique():,}")
print(f"Date range:   {agg['week'].min()} → {agg['week'].max()}")
print(f"Label balance:\n{agg['label_escalation'].value_counts(normalize=True).round(3)}")
