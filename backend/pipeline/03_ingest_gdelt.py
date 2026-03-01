"""
Step 3: GDELT News Sentiment Ingestion (Daily Grain)

Downloads GDELT 1.0 daily CSV exports for the Levant region and aggregates
them into per hex-day features, then merges into the ACLED hex-day table.

No API key required. Data is freely downloadable from data.gdeltproject.org.

Output: data/processed/acled_h3_gdelt.csv
"""

import pandas as pd
import numpy as np
import requests
import h3
import os
from zipfile import ZipFile
from io import BytesIO
from tqdm import tqdm

# ── Config ────────────────────────────────────────────────────────────────────
ACLED_H3_PATH = "data/processed/acled_h3.csv"
OUT_PATH      = "data/processed/acled_h3_gdelt.csv"

LAT_MIN, LAT_MAX = 29.5, 37.5
LON_MIN, LON_MAX = 33.5, 42.5
H3_RESOLUTION    = 6

# GDELT 1.0 column indices we care about
GDELT_COLS = {
    0:  "GlobalEventID",
    1:  "Day",             # YYYYMMDD int
    53: "ActionGeo_Lat",
    54: "ActionGeo_Long",
    30: "GoldsteinScale",  # -10 (violent) to +10 (cooperative)
    33: "NumArticles",
    34: "AvgTone",         # negative = hostile media framing
}

# ── Load ACLED H3 base ────────────────────────────────────────────────────────
print(f"Loading {ACLED_H3_PATH}...")
acled = pd.read_csv(ACLED_H3_PATH, parse_dates=["event_date"])
print(f"  {len(acled):,} hex-day rows")

date_min = acled["event_date"].min()
date_max = acled["event_date"].max()
all_dates = pd.date_range(date_min, date_max, freq="D")
print(f"  Covering {date_min.date()} → {date_max.date()}  ({len(all_dates)} days)")

# ── Download GDELT Daily Files ────────────────────────────────────────────────
def fetch_gdelt_day(date: pd.Timestamp) -> pd.DataFrame:
    """Download and parse one day of GDELT 1.0 event data for the Levant bbox.
    Caches filtered result to data/raw/gdelt_cache/YYYYMMDD.parquet.
    """
    datestr  = date.strftime("%Y%m%d")
    cache_fp = os.path.join(CACHE_DIR, f"{datestr}.parquet")
    if os.path.exists(cache_fp):
        return pd.read_parquet(cache_fp)

    url = f"http://data.gdeltproject.org/events/{datestr}.export.CSV.zip"
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200:
            return pd.DataFrame()
        zf = ZipFile(BytesIO(resp.content))
        raw = pd.read_csv(
            zf.open(zf.namelist()[0]),
            sep="\t",
            header=None,
            usecols=list(GDELT_COLS.keys()),
            low_memory=False,
            on_bad_lines="skip",
        )
        raw.rename(columns=GDELT_COLS, inplace=True)
        raw["ActionGeo_Lat"]  = pd.to_numeric(raw["ActionGeo_Lat"],  errors="coerce")
        raw["ActionGeo_Long"] = pd.to_numeric(raw["ActionGeo_Long"], errors="coerce")
        raw = raw.dropna(subset=["ActionGeo_Lat", "ActionGeo_Long"])
        raw = raw[
            (raw["ActionGeo_Lat"]  >= LAT_MIN) & (raw["ActionGeo_Lat"]  <= LAT_MAX) &
            (raw["ActionGeo_Long"] >= LON_MIN) & (raw["ActionGeo_Long"] <= LON_MAX)
        ]
        raw["EventRootCode"] = raw["EventRootCode"].astype(str).str.strip()
        raw["event_date"] = date.normalize()
        # Cache for future re-runs
        if not raw.empty:
            raw.to_parquet(cache_fp, index=False)
        return raw
    except Exception as e:
        print(f"    Warning: failed {datestr} — {e}")
        return pd.DataFrame()

print(f"\nFetching GDELT for {len(all_dates)} days...")
gdelt_rows = []
for d in tqdm(all_dates, desc="  GDELT download"):
    day_df = fetch_gdelt_day(d)
    if not day_df.empty:
        gdelt_rows.append(day_df)

if not gdelt_rows:
    print("ERROR: No GDELT data fetched.")
    exit(1)

gdelt_raw = pd.concat(gdelt_rows, ignore_index=True)
print(f"  Total GDELT events fetched: {len(gdelt_raw):,}")

# ── Assign H3 IDs ─────────────────────────────────────────────────────────────
print("Assigning H3 hex IDs to GDELT events...")
gdelt_raw["h3_id"] = gdelt_raw.apply(
    lambda r: h3.latlng_to_cell(r["ActionGeo_Lat"], r["ActionGeo_Long"], H3_RESOLUTION),
    axis=1,
)

# ── Aggregate GDELT Features per (h3_id, event_date) ─────────────────────────
print("Aggregating GDELT features per hex-day...")

gdelt_raw["GoldsteinScale"] = pd.to_numeric(gdelt_raw["GoldsteinScale"], errors="coerce")
gdelt_raw["AvgTone"]        = pd.to_numeric(gdelt_raw["AvgTone"],        errors="coerce")
gdelt_raw["NumArticles"]    = pd.to_numeric(gdelt_raw["NumArticles"],    errors="coerce")

gdelt_agg = gdelt_raw.groupby(["h3_id", "event_date"]).agg(
    gdelt_event_count   = ("GlobalEventID", "count"),
    gdelt_avg_tone      = ("AvgTone",        "mean"),
    gdelt_min_goldstein = ("GoldsteinScale", "min"),
    gdelt_avg_goldstein = ("GoldsteinScale", "mean"),
    gdelt_num_articles  = ("NumArticles",    "sum"),
).reset_index()

# Hostility score: invert tone, clamp 0-1
# AvgTone ≈ -20 to +20; more negative = more hostile media framing
gdelt_agg["gdelt_hostility"] = (
    (-gdelt_agg["gdelt_avg_tone"]).clip(lower=0) / 20.0
).clip(0, 1)

print(f"  GDELT hex-days with coverage: {len(gdelt_agg):,}")

# ── Merge into ACLED H3 panel ─────────────────────────────────────────────────
print("Merging GDELT features into ACLED H3 table...")

merged = acled.merge(gdelt_agg, on=["h3_id", "event_date"], how="left")

fill_cols = ["gdelt_event_count", "gdelt_avg_tone", "gdelt_min_goldstein",
             "gdelt_avg_goldstein", "gdelt_num_articles", "gdelt_hostility",
             "gdelt_protest_count", "gdelt_threaten_count", "gdelt_assault_count",
             "gdelt_fight_count", "gdelt_cameo_conflict"]
merged[fill_cols] = merged[fill_cols].fillna(0)

coverage = (merged["gdelt_event_count"] > 0).mean()
print(f"  GDELT coverage: {coverage:.1%} of hex-days have at least 1 GDELT event")

# ── Spatial Lag: GDELT Hostility (Vectorized) ─────────────────────────────────
print("Computing GDELT spatial lag (vectorized)...")

all_hexes = merged["h3_id"].unique()
pivot_host = merged.pivot_table(
    index="event_date", columns="h3_id", values="gdelt_hostility", fill_value=0.0
)

neighbor_map = {
    hx: [n for n in list(set(h3.grid_disk(hx, k=1)) - {hx}) if n in pivot_host.columns]
    for hx in tqdm(all_hexes, desc="  Building neighbor map")
}

neighbor_host_cols = {
    hx: (pivot_host[neighbors].mean(axis=1) if neighbors
         else pd.Series(0.0, index=pivot_host.index))
    for hx, neighbors in neighbor_map.items()
}
neighbor_host_pivot = pd.DataFrame(neighbor_host_cols, index=pivot_host.index)

nh = neighbor_host_pivot.reset_index().melt(
    id_vars="event_date", var_name="h3_id", value_name="neighbor_gdelt_hostility_avg"
)
merged = merged.merge(nh, on=["h3_id", "event_date"], how="left")
merged["neighbor_gdelt_hostility_avg"] = merged["neighbor_gdelt_hostility_avg"].fillna(0)

# Spatial lag for protest events
pivot_protest = merged.pivot_table(
    index="event_date", columns="h3_id", values="gdelt_protest_count", fill_value=0.0
)
neighbor_protest_cols = {
    hx: (pivot_protest[neighbors].mean(axis=1) if neighbors
         else pd.Series(0.0, index=pivot_protest.index))
    for hx, neighbors in neighbor_map.items()
    if hx in pivot_protest.columns
}
np_df = pd.DataFrame(neighbor_protest_cols, index=pivot_protest.index)
np_melt = np_df.reset_index().melt(
    id_vars="event_date", var_name="h3_id", value_name="neighbor_gdelt_protest_avg"
)
merged = merged.merge(np_melt, on=["h3_id", "event_date"], how="left")
merged["neighbor_gdelt_protest_avg"] = merged["neighbor_gdelt_protest_avg"].fillna(0)

# ── Save ──────────────────────────────────────────────────────────────────────
merged.to_csv(OUT_PATH, index=False)
print(f"\nSaved {len(merged):,} rows → {OUT_PATH}")
new_cols = fill_cols + ["neighbor_gdelt_hostility_avg", "neighbor_gdelt_protest_avg"]
print(f"New columns: {', '.join(new_cols)}")
