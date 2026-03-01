"""
Step 4: NASA FIRMS Thermal Anomaly Ingestion
Pulls VIIRS thermal hotspot data for the Levant region from NASA FIRMS API,
aggregates spikes per H3 hex per week, and merges into the feature table.

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

# Levant bounding box: W,S,E,N
BBOX = "33.5,29.5,42.5,37.5"

# FIRMS VIIRS S-NPP 375m — best resolution for detecting explosions, fires
FIRMS_SOURCE = "VIIRS_SNPP_NRT"

# FIRMS API base URL
FIRMS_BASE = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"

# ── Load Merged ACLED+GDELT Table ─────────────────────────────────────────────
print(f"Loading {GDELT_MERGED_PATH}...")
df = pd.read_csv(GDELT_MERGED_PATH, parse_dates=["week"])
print(f"  {len(df):,} hex-week rows")

date_min = df["week"].min()
date_max = df["week"].max() + pd.Timedelta(weeks=1)

# ── Build Weekly Date Ranges ──────────────────────────────────────────────────
# FIRMS API accepts: /csv/{MAP_KEY}/{source}/{bbox}/{days}/{date}
# Max days per request: 10. We'll pull week by week (7 days each).

all_mondays = pd.date_range(start=date_min, end=date_max, freq="W-MON")
print(f"Fetching FIRMS for {len(all_mondays)} weeks...")

def fetch_firms_week(monday: pd.Timestamp) -> pd.DataFrame:
    """Fetch VIIRS thermal hotspots for the Levant for a 7-day window starting on monday."""
    date_str = monday.strftime("%Y-%m-%d")
    url = f"{FIRMS_BASE}/{MAP_KEY}/{FIRMS_SOURCE}/{BBOX}/7/{date_str}"
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200:
            return pd.DataFrame()
        from io import StringIO
        df_raw = pd.read_csv(StringIO(resp.text))
        if df_raw.empty or "latitude" not in df_raw.columns:
            return pd.DataFrame()
        df_raw["week"] = monday
        return df_raw
    except Exception as e:
        print(f"    Warning: failed {date_str} — {e}")
        return pd.DataFrame()

firms_rows = []
for monday in tqdm(all_mondays, desc="  FIRMS download"):
    chunk = fetch_firms_week(monday)
    if not chunk.empty:
        firms_rows.append(chunk)

if not firms_rows:
    print("WARNING: No FIRMS data fetched. Check your MAP_KEY and internet connection.")
    # Still save the file without FIRMS features (filled with zeros)
    df["firms_hotspot_count"] = 0
    df["firms_avg_frp"]       = 0.0
    df["firms_max_frp"]       = 0.0
    df["firms_spike"]         = 0
    df.to_csv(OUT_PATH, index=False)
    print(f"Saved (no FIRMS) {len(df):,} rows to {OUT_PATH}")
    exit(0)

firms_raw = pd.concat(firms_rows, ignore_index=True)
print(f"  Total FIRMS detections: {len(firms_raw):,}")

# ── Assign H3 IDs ─────────────────────────────────────────────────────────────
print("Assigning H3 hex IDs to FIRMS detections...")
firms_raw["latitude"]  = pd.to_numeric(firms_raw["latitude"],  errors="coerce")
firms_raw["longitude"] = pd.to_numeric(firms_raw["longitude"], errors="coerce")
firms_raw = firms_raw.dropna(subset=["latitude", "longitude"])

firms_raw["h3_id"] = firms_raw.apply(
    lambda r: h3.latlng_to_cell(r["latitude"], r["longitude"], H3_RESOLUTION),
    axis=1
)

# FRP = Fire Radiative Power (MW) — proxy for intensity of thermal event
firms_raw["frp"] = pd.to_numeric(firms_raw.get("frp", firms_raw.get("FRP", 0)), errors="coerce").fillna(0)

# ── Aggregate per (h3_id, week) ───────────────────────────────────────────────
print("Aggregating FIRMS features per hex-week...")

firms_agg = firms_raw.groupby(["h3_id", "week"]).agg(
    firms_hotspot_count = ("frp", "count"),
    firms_avg_frp       = ("frp", "mean"),
    firms_max_frp       = ("frp", "max"),
).reset_index()

# Spike flag: >= 3 hotspots in a hex in one week is anomalous for this region
firms_agg["firms_spike"] = (firms_agg["firms_hotspot_count"] >= 3).astype(int)

print(f"  FIRMS hex-weeks with detections: {len(firms_agg):,}")

# ── Merge ─────────────────────────────────────────────────────────────────────
print("Merging FIRMS into feature table...")

merged = df.merge(firms_agg, on=["h3_id", "week"], how="left")
merged["firms_hotspot_count"].fillna(0, inplace=True)
merged["firms_avg_frp"].fillna(0,       inplace=True)
merged["firms_max_frp"].fillna(0,       inplace=True)
merged["firms_spike"].fillna(0,         inplace=True)

coverage = (merged["firms_hotspot_count"] > 0).mean()
print(f"  FIRMS coverage: {coverage:.1%} of hex-weeks have at least 1 thermal detection")

# ── Save ──────────────────────────────────────────────────────────────────────
merged.to_csv(OUT_PATH, index=False)
print(f"\nSaved {len(merged):,} rows to {OUT_PATH}")
print("New columns: firms_hotspot_count, firms_avg_frp, firms_max_frp, firms_spike")
