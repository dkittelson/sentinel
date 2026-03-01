"""
Step 1: ACLED Data Preprocessing + H3 Binning
Ingests raw ACLED CSV, cleans it, and aggregates events into H3 hexagonal grid cells.
Now includes velocity/momentum features and spatial lag features.
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

# ── Actor Novelty Pre-computation ────────────────────────────────────────────
# Track unique actor pairs per hex-week. New pairs (never seen before in this hex)
# are a strong leading indicator — a new armed group entering a hex often precedes
# the first violent event by 1-2 weeks.
print("Computing actor novelty features...")

df["actor_pair"] = (
    df["actor1"].fillna("unknown") + "||" + df["actor2"].fillna("unknown")
)

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
    actor_pair_count  = ("actor_pair", "nunique"),  # distinct actor1-actor2 combos
).reset_index()

# Actor pair velocity: change in unique actor pairs vs prior week
# Spike in new actor combinations = new actors entering the conflict space
agg = agg.sort_values(["h3_id", "week"])
agg["actor_pair_delta"] = (
    agg.groupby("h3_id")["actor_pair_count"].diff().fillna(0)
)
agg["actor_pair_roll4w"] = (
    agg.groupby("h3_id")["actor_pair_count"]
    .transform(lambda x: x.rolling(4, min_periods=1).mean())
)
agg["actor_pair_velocity"] = (
    agg["actor_pair_count"] / (agg["actor_pair_roll4w"] + 1e-6)
)

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

# ── Velocity / Momentum Features ─────────────────────────────────────────────
# These capture acceleration, not just absolute level — key for distinguishing
# a chronically active hex from one that is *suddenly* spiking.
print("Computing velocity features...")

agg["event_count_delta"] = (
    agg.groupby("h3_id")["event_count"].diff().fillna(0)
)
agg["fatality_delta"] = (
    agg.groupby("h3_id")["total_fatalities"].diff().fillna(0)
)
# Velocity ratio: this week vs 4-week baseline (>1.0 means spiking above baseline)
agg["event_velocity"] = (
    agg["event_count"] / (agg["event_count_roll4w"] + 1e-6)
)
agg["fatality_velocity"] = (
    agg["total_fatalities"] / (agg["fatalities_roll4w"] + 1e-6)
)

# ── Spatial Lag Features ──────────────────────────────────────────────────────
# For each hex-week, compute the average/sum activity in its ring-1 H3 neighbors.
# Conflict spills over spatially — neighboring hex escalation is a strong predictor.
print("Computing spatial lag features (this may take ~1 minute)...")

# Build a lookup: h3_id → week → event_count / fatalities
pivot_events = agg.pivot_table(
    index="week", columns="h3_id", values="event_count", fill_value=0
)
pivot_fatal = agg.pivot_table(
    index="week", columns="h3_id", values="total_fatalities", fill_value=0
)

all_hexes = agg["h3_id"].unique()

neighbor_event_avg = []
neighbor_fatal_sum = []

for _, row in tqdm(agg.iterrows(), total=len(agg), desc="  Spatial lag"):
    neighbors = list(set(h3.grid_disk(row["h3_id"], k=1)) - {row["h3_id"]})
    # Only include neighbors that exist in our dataset
    valid = [n for n in neighbors if n in pivot_events.columns]
    week  = row["week"]
    if valid and week in pivot_events.index:
        neighbor_event_avg.append(pivot_events.loc[week, valid].mean())
        neighbor_fatal_sum.append(pivot_fatal.loc[week, valid].sum())
    else:
        neighbor_event_avg.append(0.0)
        neighbor_fatal_sum.append(0.0)

agg["neighbor_event_avg"] = neighbor_event_avg
agg["neighbor_fatal_sum"] = neighbor_fatal_sum

# ── Labels ───────────────────────────────────────────────────────────────────
print("Generating labels...")

agg["next_week_events"]     = agg.groupby("h3_id")["event_count"].shift(-1)
agg["next_week_fatalities"] = agg.groupby("h3_id")["total_fatalities"].shift(-1)

# Primary label (NEW): will ANY fatality occur in this hex next week?
# This is more directly relevant for civilian danger than tracking event count trends.
agg["label_escalation"] = (
    (agg["next_week_fatalities"] > 0).astype(int)
)

# Secondary label (OLD, kept for reference): did event count increase?
agg["label_trend"] = (
    (agg["next_week_events"] > agg["event_count"]).astype(int)
)

# Drop the last week per hex (no label available)
agg = agg.dropna(subset=["next_week_fatalities"])

# ── Save ──────────────────────────────────────────────────────────────────────
agg.to_csv(OUT_PATH, index=False)
print(f"\nSaved {len(agg):,} hex-week rows to {OUT_PATH}")
print(f"Unique hexes:  {agg['h3_id'].nunique():,}")
print(f"Date range:    {agg['week'].min()} → {agg['week'].max()}")
print(f"Label balance (fatality next week):")
print(f"{agg['label_escalation'].value_counts(normalize=True).round(3)}")
print(f"\nOld label balance (event count increase):")
print(f"{agg['label_trend'].value_counts(normalize=True).round(3)}")
