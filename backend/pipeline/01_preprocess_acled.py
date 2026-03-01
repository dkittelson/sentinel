"""
Step 1: ACLED Data Preprocessing + H3 Binning (Daily Grain, 48h Lookahead)

Aggregates ACLED events into H3 hex-day cells and labels each cell:
  next_48h_dangerous = 1  if ANY dangerous event occurs in that hex within the next 48 hours

"Dangerous" = anything that threatens an ordinary civilian:
  - All Battles (armed clashes, territorial takeovers)
  - All Explosions/Remote violence (airstrikes, IEDs, shelling)
  - All Violence against civilians (attacks, abductions, sexual violence, suicide bombs)
  - All Riots (mob violence, looting, violent demonstrations)
  - Violent protest subtypes (excessive force, protest with intervention)

Excludes Strategic developments (non-violent admin events) and peaceful protests.

Output: data/processed/acled_h3.csv
"""

import pandas as pd
import h3
import numpy as np
from tqdm import tqdm

# ── Config ────────────────────────────────────────────────────────────────────
RAW_PATH = "data/raw/ACLED Data_2026-03-01.csv"
OUT_PATH  = "data/processed/acled_h3.csv"

H3_RESOLUTION    = 6   # ~36 km² hexagons
GEO_PRECISION_MAX = 2  # 1=exact, 2=town-level; drop village-approximated coords

# Event types where ALL sub-events are dangerous to civilians
DANGEROUS_TYPES = {
    "Battles",
    "Explosions/Remote violence",
    "Violence against civilians",
    "Riots",
}

# Protest sub-events that are dangerous (police/military violence at demonstrations)
DANGEROUS_PROTEST_SUBS = {
    "Excessive force against protesters",
    "Protest with intervention",
    "Violent demonstration",
}

# ── Load ──────────────────────────────────────────────────────────────────────
print(f"Loading {RAW_PATH}...")
df = pd.read_csv(RAW_PATH, low_memory=False)
print(f"  Raw rows: {len(df):,}")

# ── Clean ─────────────────────────────────────────────────────────────────────
df["event_date"] = pd.to_datetime(df["event_date"], dayfirst=True, errors="coerce")
df = df.dropna(subset=["event_date", "latitude", "longitude"])
df = df[df["geo_precision"] <= GEO_PRECISION_MAX]

df["fatalities"]      = pd.to_numeric(df["fatalities"],      errors="coerce").fillna(0)
df["population_best"] = pd.to_numeric(df["population_best"], errors="coerce").fillna(0)

print(f"  After cleaning: {len(df):,} rows")

# ── Flag Dangerous Events ─────────────────────────────────────────────────────
# "Dangerous" = anything that threatens an ordinary civilian's life or safety.
# Excludes Strategic developments (non-violent admin) and peaceful protests.
df["is_dangerous"] = (
    df["event_type"].isin(DANGEROUS_TYPES) |
    df["sub_event_type"].isin(DANGEROUS_PROTEST_SUBS)
).astype(int)

# Per-type flags for feature engineering
df["is_battle"]    = (df["event_type"] == "Battles").astype(int)
df["is_explosion"] = (df["event_type"] == "Explosions/Remote violence").astype(int)
df["is_vac"]       = (df["event_type"] == "Violence against civilians").astype(int)
df["is_riot"]      = (df["event_type"] == "Riots").astype(int)

print(f"  Dangerous events: {df['is_dangerous'].sum():,} / {len(df):,} "
      f"({df['is_dangerous'].mean()*100:.1f}%)")

# ── H3 Binning ────────────────────────────────────────────────────────────────
print(f"Assigning H3 resolution-{H3_RESOLUTION} hex IDs...")
df["h3_id"] = df.apply(
    lambda row: h3.latlng_to_cell(row["latitude"], row["longitude"], H3_RESOLUTION),
    axis=1,
)

# ── Actor Novelty Pre-computation ────────────────────────────────────────────
df["actor_pair"] = (
    df["actor1"].fillna("unknown") + "||" + df["actor2"].fillna("unknown")
)

# ── Aggregate per (h3_id, date) ──────────────────────────────────────────────
print("Aggregating features per hex-day...")

agg = df.groupby(["h3_id", "event_date"]).agg(
    event_count       = ("event_type",      "count"),
    dangerous_count   = ("is_dangerous",    "sum"),
    total_fatalities  = ("fatalities",       "sum"),
    max_fatalities    = ("fatalities",       "max"),
    battle_count      = ("is_battle",        "sum"),
    explosion_count   = ("is_explosion",     "sum"),
    vac_count         = ("is_vac",           "sum"),
    riot_count        = ("is_riot",          "sum"),
    population_best   = ("population_best",  "max"),
    unique_actors     = ("actor1",           "nunique"),
    actor_pair_count  = ("actor_pair",       "nunique"),
).reset_index()

# ── Build Complete Hex-Day Panel ──────────────────────────────────────────────
# Expand to every (hex, day) combination so rolling windows work correctly.
# Missing days (no events) get zero-fill — the model must learn that silence matters.
print("Building complete hex-day panel (every hex × every day)...")

all_hexes = agg["h3_id"].unique()
all_dates = pd.date_range(agg["event_date"].min(), agg["event_date"].max(), freq="D")

idx = pd.MultiIndex.from_product([all_hexes, all_dates], names=["h3_id", "event_date"])
panel = (
    agg.set_index(["h3_id", "event_date"])
    .reindex(idx, fill_value=0)
    .reset_index()
)

# population_best is static per location — forward/backfill within hex
panel["population_best"] = (
    panel.groupby("h3_id")["population_best"]
    .transform(lambda x: x.replace(0, np.nan).ffill().bfill().fillna(0))
)

print(f"  Panel size: {len(panel):,} hex-day rows  |  {len(all_hexes):,} hexes  |  {len(all_dates):,} days")

# ── Rolling Features ─────────────────────────────────────────────────────────
print("Computing rolling features (3d, 7d, 14d)...")

panel = panel.sort_values(["h3_id", "event_date"])

for window, label in [(3, "3d"), (7, "7d"), (14, "14d")]:
    panel[f"dangerous_roll{label}"] = (
        panel.groupby("h3_id")["dangerous_count"]
        .transform(lambda x: x.rolling(window, min_periods=1).mean())
    )
    panel[f"fatalities_roll{label}"] = (
        panel.groupby("h3_id")["total_fatalities"]
        .transform(lambda x: x.rolling(window, min_periods=1).mean())
    )
    panel[f"event_roll{label}"] = (
        panel.groupby("h3_id")["event_count"]
        .transform(lambda x: x.rolling(window, min_periods=1).mean())
    )

# ── Velocity / Momentum Features ─────────────────────────────────────────────
panel["dangerous_delta"] = (
    panel.groupby("h3_id")["dangerous_count"].diff().fillna(0)
)
panel["fatality_delta"] = (
    panel.groupby("h3_id")["total_fatalities"].diff().fillna(0)
)
# Velocity: today vs 14-day baseline (>1.0 means spiking above normal)
panel["dangerous_velocity"] = (
    panel["dangerous_count"] / (panel["dangerous_roll14d"] + 1e-6)
)
panel["fatality_velocity"] = (
    panel["total_fatalities"] / (panel["fatalities_roll14d"] + 1e-6)
)

# ── Actor Novelty Features ───────────────────────────────────────────────────
panel["actor_pair_delta"] = (
    panel.groupby("h3_id")["actor_pair_count"].diff().fillna(0)
)
panel["actor_pair_roll14d"] = (
    panel.groupby("h3_id")["actor_pair_count"]
    .transform(lambda x: x.rolling(14, min_periods=1).mean())
)
panel["actor_pair_velocity"] = (
    panel["actor_pair_count"] / (panel["actor_pair_roll14d"] + 1e-6)
)

# ── Spatial Lag Features ──────────────────────────────────────────────────────
# Vectorized approach: build pivot → compute neighbor mean per hex column.
# Much faster than row-by-row loop (2,973 hexes × N neighbors vs 5.4M row iterations).
print("Computing spatial lag features (H3 ring-1 neighbors, vectorized)...")

pivot_danger = panel.pivot_table(
    index="event_date", columns="h3_id", values="dangerous_count", fill_value=0
)
pivot_fatal = panel.pivot_table(
    index="event_date", columns="h3_id", values="total_fatalities", fill_value=0
)

all_hexes = panel["h3_id"].unique()

# Build neighbor map once
neighbor_map = {
    hx: [n for n in list(set(h3.grid_disk(hx, k=1)) - {hx}) if n in pivot_danger.columns]
    for hx in tqdm(all_hexes, desc="  Building neighbor map")
}

# Vectorized: for each hex, average its valid neighbors' columns
neighbor_danger_cols = {}
neighbor_fatal_cols  = {}
for hx, neighbors in neighbor_map.items():
    if neighbors:
        neighbor_danger_cols[hx] = pivot_danger[neighbors].mean(axis=1)
        neighbor_fatal_cols[hx]  = pivot_fatal[neighbors].sum(axis=1)
    else:
        neighbor_danger_cols[hx] = pd.Series(0.0, index=pivot_danger.index)
        neighbor_fatal_cols[hx]  = pd.Series(0.0, index=pivot_fatal.index)

neighbor_danger_pivot = pd.DataFrame(neighbor_danger_cols, index=pivot_danger.index)
neighbor_fatal_pivot  = pd.DataFrame(neighbor_fatal_cols,  index=pivot_fatal.index)

# Melt back to long format and merge
nd = neighbor_danger_pivot.reset_index().melt(id_vars="event_date", var_name="h3_id", value_name="neighbor_danger_avg")
nf = neighbor_fatal_pivot.reset_index().melt(id_vars="event_date",  var_name="h3_id", value_name="neighbor_fatal_sum")

panel = panel.merge(nd, on=["h3_id", "event_date"], how="left")
panel = panel.merge(nf, on=["h3_id", "event_date"], how="left")
panel[["neighbor_danger_avg", "neighbor_fatal_sum"]] = panel[["neighbor_danger_avg", "neighbor_fatal_sum"]].fillna(0)


# ── Label: next 72 hours ──────────────────────────────────────────────────────
print("Generating 72h danger label...")

# A hex is "dangerous" in the next 72h if ANY dangerous event occurs
# in t+1, t+2, OR t+3. We take the max so any day triggers a positive.
panel["_next_1d"] = panel.groupby("h3_id")["dangerous_count"].shift(-1).fillna(0)
panel["_next_2d"] = panel.groupby("h3_id")["dangerous_count"].shift(-2).fillna(0)
panel["_next_3d"] = panel.groupby("h3_id")["dangerous_count"].shift(-3).fillna(0)
panel["next_72h_dangerous_raw"] = panel[["_next_1d", "_next_2d", "_next_3d"]].max(axis=1)
panel["label"] = (panel["next_72h_dangerous_raw"] > 0).astype(int)
panel = panel.drop(columns=["_next_1d", "_next_2d", "_next_3d", "next_72h_dangerous_raw"])

# Drop the last 3 days per hex (no valid 72h lookahead window)
# Use rank-from-end to avoid groupby.apply dropping h3_id in pandas 2.x
panel = panel.sort_values(["h3_id", "event_date"])
panel["_rank_end"] = panel.groupby("h3_id").cumcount(ascending=False)
panel = panel[panel["_rank_end"] >= 3].drop(columns=["_rank_end"]).reset_index(drop=True)

label_balance = panel["label"].value_counts(normalize=True).round(3).to_dict()
print(f"  Label balance: {label_balance}")

# ── Save ──────────────────────────────────────────────────────────────────────
panel.to_csv(OUT_PATH, index=False)
print(f"\nSaved {len(panel):,} hex-day rows → {OUT_PATH}")
print(f"Unique hexes: {panel['h3_id'].nunique():,}  |  "
      f"Date range: {panel['event_date'].min().date()} → {panel['event_date'].max().date()}")

