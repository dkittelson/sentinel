"""
Step 3: GDELT News Sentiment Ingestion
Pulls GDELT 2.0 event data for the Levant region, computes a weekly news sentiment
score per H3 hex, and merges it into the processed ACLED feature table.

GDELT requires no API key. Data is queried via Google BigQuery public datasets
OR via the gdelt Python package (offline CSV approach used here for simplicity).

Output: data/processed/acled_h3_gdelt.csv
"""

import pandas as pd
import numpy as np
import requests
import h3
import os
from io import StringIO
from tqdm import tqdm

# ── Config ────────────────────────────────────────────────────────────────────
ACLED_H3_PATH = "data/processed/acled_h3.csv"
OUT_PATH      = "data/processed/acled_h3_gdelt.csv"

# Levant bounding box: Lebanon, northern Israel, southern Syria
# GDELT ActionGeo lat/lon range
LAT_MIN, LAT_MAX = 29.5, 37.5
LON_MIN, LON_MAX = 33.5, 42.5

H3_RESOLUTION = 6

# GDELT GKG (Global Knowledge Graph) tone scale: negative = hostile/conflict framing
# We use event-level GDELT 1.0 which is freely downloadable as daily CSVs
# Event columns we care about: ActionGeo_Lat, ActionGeo_Long, AvgTone, NumArticles, GoldsteinScale

GDELT_COLS = {
    0:  "GlobalEventID",
    1:  "Day",           # YYYYMMDD
    53: "ActionGeo_Lat",
    54: "ActionGeo_Long",
    30: "GoldsteinScale",  # -10 (violent) to +10 (cooperative)
    31: "NumMentions",
    32: "NumSources",
    33: "NumArticles",
    34: "AvgTone",         # negative = hostile framing
}

# ── Load ACLED H3 base ────────────────────────────────────────────────────────
print(f"Loading {ACLED_H3_PATH}...")
acled = pd.read_csv(ACLED_H3_PATH, parse_dates=["week"])
print(f"  {len(acled):,} hex-week rows")

# Get the date range we need to cover
date_min = acled["week"].min()
date_max = acled["week"].max() + pd.Timedelta(weeks=1)
print(f"  Covering {date_min.date()} -> {date_max.date()}")

# ── Download GDELT Daily Files ────────────────────────────────────────────────
# GDELT 1.0 daily export: http://data.gdeltproject.org/events/YYYYMMDD.export.CSV.zip
# We sample every 7th day (weekly) to keep download size manageable

def fetch_gdelt_day(date: pd.Timestamp) -> pd.DataFrame:
    """Download and parse one day of GDELT 1.0 event data."""
    datestr = date.strftime("%Y%m%d")
    url = f"http://data.gdeltproject.org/events/{datestr}.export.CSV.zip"
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200:
            return pd.DataFrame()
        # Read zip'd CSV
        from zipfile import ZipFile
        from io import BytesIO
        zf = ZipFile(BytesIO(resp.content))
        fname = zf.namelist()[0]
        raw = pd.read_csv(
            zf.open(fname),
            sep="\t",
            header=None,
            usecols=list(GDELT_COLS.keys()),
            low_memory=False,
            on_bad_lines="skip",
        )
        raw.rename(columns=GDELT_COLS, inplace=True)
        # Filter to Levant bounding box
        raw = raw.dropna(subset=["ActionGeo_Lat", "ActionGeo_Long"])
        raw["ActionGeo_Lat"]  = pd.to_numeric(raw["ActionGeo_Lat"],  errors="coerce")
        raw["ActionGeo_Long"] = pd.to_numeric(raw["ActionGeo_Long"], errors="coerce")
        raw = raw[
            (raw["ActionGeo_Lat"]  >= LAT_MIN) & (raw["ActionGeo_Lat"]  <= LAT_MAX) &
            (raw["ActionGeo_Long"] >= LON_MIN) & (raw["ActionGeo_Long"] <= LON_MAX)
        ]
        return raw
    except Exception as e:
        print(f"    Warning: failed {datestr} — {e}")
        return pd.DataFrame()

# Sample weekly (every Monday) to build our weekly dataset
all_mondays = pd.date_range(start=date_min, end=date_max, freq="W-MON")
print(f"\nFetching GDELT for {len(all_mondays)} weeks (one file per week)...")

gdelt_rows = []
for monday in tqdm(all_mondays, desc="  GDELT download"):
    df_day = fetch_gdelt_day(monday)
    if df_day.empty:
        continue
    df_day["week"] = monday
    gdelt_rows.append(df_day)

if not gdelt_rows:
    print("ERROR: No GDELT data fetched. Check internet connection.")
    exit(1)

gdelt_raw = pd.concat(gdelt_rows, ignore_index=True)
print(f"  Total GDELT events fetched: {len(gdelt_raw):,}")

# ── Assign H3 IDs ─────────────────────────────────────────────────────────────
print("Assigning H3 hex IDs to GDELT events...")
gdelt_raw["h3_id"] = gdelt_raw.apply(
    lambda r: h3.latlng_to_cell(r["ActionGeo_Lat"], r["ActionGeo_Long"], H3_RESOLUTION),
    axis=1
)

# ── Aggregate GDELT Features per (h3_id, week) ───────────────────────────────
print("Aggregating GDELT features per hex-week...")

gdelt_raw["GoldsteinScale"] = pd.to_numeric(gdelt_raw["GoldsteinScale"], errors="coerce")
gdelt_raw["AvgTone"]        = pd.to_numeric(gdelt_raw["AvgTone"],        errors="coerce")
gdelt_raw["NumArticles"]    = pd.to_numeric(gdelt_raw["NumArticles"],    errors="coerce")

gdelt_agg = gdelt_raw.groupby(["h3_id", "week"]).agg(
    gdelt_event_count    = ("GlobalEventID",  "count"),
    gdelt_avg_tone       = ("AvgTone",         "mean"),   # negative = more hostile
    gdelt_min_goldstein  = ("GoldsteinScale",  "min"),    # most destabilizing event
    gdelt_avg_goldstein  = ("GoldsteinScale",  "mean"),
    gdelt_num_articles   = ("NumArticles",     "sum"),    # media attention volume
).reset_index()

# Hostility score: invert tone and clamp to 0-1 scale
# AvgTone ranges roughly -20 to +20; more negative = more hostile coverage
gdelt_agg["gdelt_hostility"] = (
    (-gdelt_agg["gdelt_avg_tone"]).clip(lower=0) / 20.0
).clip(0, 1)

print(f"  GDELT hex-weeks: {len(gdelt_agg):,}")

# ── Merge into ACLED H3 table ─────────────────────────────────────────────────
print("Merging GDELT features into ACLED H3 table...")

merged = acled.merge(gdelt_agg, on=["h3_id", "week"], how="left")

# Fill nulls (hexes with no GDELT coverage that week) with neutral values
fill_cols = ["gdelt_event_count", "gdelt_avg_tone", "gdelt_min_goldstein",
             "gdelt_avg_goldstein", "gdelt_num_articles", "gdelt_hostility"]
merged[fill_cols] = merged[fill_cols].fillna(0)

coverage = (merged["gdelt_event_count"] > 0).mean()
print(f"  GDELT coverage: {coverage:.1%} of hex-weeks have at least 1 GDELT event")

# ── Spatial Lag: GDELT Hostility ──────────────────────────────────────────────
# For each hex-week, compute the average GDELT hostility of its ring-1 neighbors.
# This lets a news-hostile hex "bleed" signal to bordering hexes, producing the
# probability gradient ring on the map rather than isolated point spikes.
print("Computing GDELT spatial lag (neighbor_gdelt_hostility_avg)...")

pivot_hostility = merged.pivot_table(
    index="week", columns="h3_id", values="gdelt_hostility", fill_value=0.0
)

neighbor_gdelt_hostility_avg = []
for _, row in tqdm(merged.iterrows(), total=len(merged), desc="  GDELT spatial lag"):
    neighbors = list(set(h3.grid_disk(row["h3_id"], k=1)) - {row["h3_id"]})
    valid = [n for n in neighbors if n in pivot_hostility.columns]
    week  = row["week"]
    if valid and week in pivot_hostility.index:
        neighbor_gdelt_hostility_avg.append(pivot_hostility.loc[week, valid].mean())
    else:
        neighbor_gdelt_hostility_avg.append(0.0)

merged["neighbor_gdelt_hostility_avg"] = neighbor_gdelt_hostility_avg

# ── Save ──────────────────────────────────────────────────────────────────────
merged.to_csv(OUT_PATH, index=False)
print(f"\nSaved {len(merged):,} rows to {OUT_PATH}")
print(f"New columns: gdelt_event_count, gdelt_avg_tone, gdelt_min_goldstein, gdelt_avg_goldstein, gdelt_num_articles, gdelt_hostility, neighbor_gdelt_hostility_avg")
