"""
Step 4: NASA FIRMS Thermal Anomaly Ingestion (Daily Grain)

Pulls VIIRS/SNPP thermal hotspot data for the Levant from NASA FIRMS API,
aggregates per hex-day, and merges into the ACLED+GDELT feature table.

Requires a free MAP_KEY from earthdata.nasa.gov.
Set FIRMS_MAP_KEY in your .env file.

Output: data/processed/acled_h3_gdelt_firms.csv
"""

import pandas as pd
import numpy as np
import requests
import h3
import os
from dotenv import load_dotenv
from tqdm import tqdm
from io import StringIO

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
GDELT_MERGED_PATH = "data/processed/acled_h3_gdelt.csv"
OUT_PATH          = "data/processed/acled_h3_gdelt_firms.csv"

MAP_KEY = os.getenv("FIRMS_MAP_KEY")
if not MAP_KEY:
    raise RuntimeError(
        "FIRMS_MAP_KEY not set. Get a free MAP_KEY at earthdata.nasa.gov "
        "and add it to your .env file as: FIRMS_MAP_KEY=your_key_here"
    )

H3_RESOLUTION = 6
BBOX          = "33.5,29.5,42.5,37.5"   # W,S,E,N — Levant corridor
FIRMS_SOURCE  = "VIIRS_SNPP_SP"          # SP = full archive back to 2012
FIRMS_BASE    = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
CHUNK_DAYS    = 5                         # max safe window for SP source

# ── Load ACLED+GDELT Table ────────────────────────────────────────────────────
print(f"Loading {GDELT_MERGED_PATH}...")
df = pd.read_csv(GDELT_MERGED_PATH, parse_dates=["event_date"])
print(f"  {len(df):,} hex-day rows")

date_min = df["event_date"].min()
date_max = df["event_date"].max()

# ── Build Chunk Date Ranges ───────────────────────────────────────────────────
# Fetch FIRMS in 5-day windows; detect each fire's exact day via acq_date column
chunk_starts = pd.date_range(start=date_min, end=date_max, freq=f"{CHUNK_DAYS}D")
print(f"Fetching FIRMS for {len(chunk_starts)} chunks ({CHUNK_DAYS}-day windows)...")

def fetch_firms_chunk(start: pd.Timestamp) -> pd.DataFrame:
    date_str = start.strftime("%Y-%m-%d")
    url = f"{FIRMS_BASE}/{MAP_KEY}/{FIRMS_SOURCE}/{BBOX}/{CHUNK_DAYS}/{date_str}"
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200:
            return pd.DataFrame()
        raw = pd.read_csv(StringIO(resp.text))
        if raw.empty or "latitude" not in raw.columns:
            return pd.DataFrame()
        return raw
    except Exception as e:
        print(f"    Warning: failed {date_str} — {e}")
        return pd.DataFrame()

firms_rows = []
for start in tqdm(chunk_starts, desc="  FIRMS download"):
    chunk = fetch_firms_chunk(start)
    if not chunk.empty:
        firms_rows.append(chunk)

if not firms_rows:
    print("WARNING: No FIRMS data fetched. Saving with zero FIRMS features.")
    for col in ["firms_hotspot_count", "firms_avg_frp", "firms_max_frp",
                "firms_spike", "neighbor_firms_spike_sum"]:
        df[col] = 0
    df.to_csv(OUT_PATH, index=False)
    print(f"Saved (no FIRMS) {len(df):,} rows → {OUT_PATH}")
    exit(0)

firms_raw = pd.concat(firms_rows, ignore_index=True)
print(f"  Total FIRMS detections: {len(firms_raw):,}")

# ── Parse acquisition date (daily precision) ──────────────────────────────────
# FIRMS SP contains `acq_date` column in YYYY-MM-DD format
firms_raw["latitude"]  = pd.to_numeric(firms_raw["latitude"],  errors="coerce")
firms_raw["longitude"] = pd.to_numeric(firms_raw["longitude"], errors="coerce")
firms_raw = firms_raw.dropna(subset=["latitude", "longitude"])

if "acq_date" in firms_raw.columns:
    firms_raw["event_date"] = pd.to_datetime(firms_raw["acq_date"], errors="coerce")
else:
    # Fallback: derive from acq_date or use acq_datetime
    firms_raw["event_date"] = pd.to_datetime(
        firms_raw.get("acq_datetime", firms_raw.index), errors="coerce"
    ).dt.normalize()

firms_raw = firms_raw.dropna(subset=["event_date"])
firms_raw["event_date"] = firms_raw["event_date"].dt.normalize()

# ── Assign H3 IDs ─────────────────────────────────────────────────────────────
print("Assigning H3 hex IDs to FIRMS detections...")
firms_raw["h3_id"] = firms_raw.apply(
    lambda r: h3.latlng_to_cell(r["latitude"], r["longitude"], H3_RESOLUTION),
    axis=1,
)

# FRP = Fire Radiative Power (MW) — proxy for burn/explosion intensity
frp_col = "frp" if "frp" in firms_raw.columns else "FRP"
firms_raw["frp"] = pd.to_numeric(firms_raw.get(frp_col, 0), errors="coerce").fillna(0)

# ── Aggregate per (h3_id, event_date) ────────────────────────────────────────
print("Aggregating FIRMS features per hex-day...")

firms_agg = firms_raw.groupby(["h3_id", "event_date"]).agg(
    firms_hotspot_count = ("frp", "count"),
    firms_avg_frp       = ("frp", "mean"),
    firms_max_frp       = ("frp", "max"),
).reset_index()

# Spike flag: >= 2 hotspots in a single hex-day is anomalous at daily resolution
firms_agg["firms_spike"] = (firms_agg["firms_hotspot_count"] >= 2).astype(int)

print(f"  FIRMS hex-days with detections: {len(firms_agg):,}")

# ── Merge ─────────────────────────────────────────────────────────────────────
print("Merging FIRMS into feature table...")

merged = df.merge(firms_agg, on=["h3_id", "event_date"], how="left")
fill_cols = ["firms_hotspot_count", "firms_avg_frp", "firms_max_frp", "firms_spike"]
merged[fill_cols] = merged[fill_cols].fillna(0)

coverage = (merged["firms_hotspot_count"] > 0).mean()
print(f"  FIRMS coverage: {coverage:.1%} of hex-days have at least 1 thermal detection")

# ── Spatial Lag: FIRMS Spike (Vectorized) ────────────────────────────────────
print("Computing FIRMS spatial lag (vectorized)...")

all_hexes = merged["h3_id"].unique()
pivot_spike = merged.pivot_table(
    index="event_date", columns="h3_id", values="firms_spike", fill_value=0
)

neighbor_map = {
    hx: [n for n in list(set(h3.grid_disk(hx, k=1)) - {hx}) if n in pivot_spike.columns]
    for hx in tqdm(all_hexes, desc="  Building neighbor map")
}

neighbor_spike_cols = {
    hx: (pivot_spike[neighbors].sum(axis=1) if neighbors
         else pd.Series(0, index=pivot_spike.index))
    for hx, neighbors in neighbor_map.items()
}
neighbor_spike_pivot = pd.DataFrame(neighbor_spike_cols, index=pivot_spike.index)

ns = neighbor_spike_pivot.reset_index().melt(
    id_vars="event_date", var_name="h3_id", value_name="neighbor_firms_spike_sum"
)
merged = merged.merge(ns, on=["h3_id", "event_date"], how="left")
merged["neighbor_firms_spike_sum"] = merged["neighbor_firms_spike_sum"].fillna(0).astype(int)

# ── Save ──────────────────────────────────────────────────────────────────────
merged.to_csv(OUT_PATH, index=False)
print(f"\nSaved {len(merged):,} rows → {OUT_PATH}")
print("New columns: firms_hotspot_count, firms_avg_frp, firms_max_frp, firms_spike, neighbor_firms_spike_sum")

