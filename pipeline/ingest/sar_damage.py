"""Sentinel-1 SAR battle damage detection for the Levant.

Uses the Pixel-Wise T-Test (PWTT) method (Ballinger et al., RSE 2025) to detect
building damage from Sentinel-1 SAR imagery via Google Earth Engine.

Reference: https://arxiv.org/abs/2405.06323
Code:      https://github.com/oballinger/PWTT

Algorithm: For each pixel, compare the distribution of Sentinel-1 VV backscatter
during a stable reference period (pre-war) against an inference period (post-war).
A one-sided Welch's t-test flags pixels where backscatter dropped significantly —
structural damage consistently lowers radar return. Per-hex stats are then
aggregated from pixel-level results.

Output: pipeline/data/processed/sar_damage_hex_daily.parquet
Columns:
  h3_id              — H3 resolution-6 hex ID
  date               — inference window end date
  damage_mean        — mean PWTT t-statistic across hex (higher = more damage signal)
  damage_fraction    — fraction of hex pixels exceeding damage threshold
  damage_velocity_7d — change in damage_mean vs 7 days prior
  damage_zscore      — how anomalous is this hex vs its own 30-day baseline

Usage:
  python pipeline/ingest/sar_damage.py                    # current 30-day window
  python pipeline/ingest/sar_damage.py --backfill         # monthly from Oct 2023
  python pipeline/ingest/sar_damage.py --date 2024-06-01  # specific inference end date
"""

import ee
import h3
import pandas as pd
import numpy as np
import os
import sys
import json
import argparse
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ml.config import H3_RESOLUTION, ZSCORE_WINDOW, ZSCORE_MIN_PERIODS, ZSCORE_CLIP

OUTPUT = os.path.join(os.path.dirname(__file__), "..", "data", "processed",
                      "sar_damage_hex_daily.parquet")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")

# ── SAR Config ────────────────────────────────────────────────────────────────
# Reference period: stable pre-war baseline. Ends day before Oct 7 2023.
REFERENCE_START = "2022-01-01"
REFERENCE_END   = "2023-10-06"

# Inference window: rolling 30-day window ending at the requested date
INFERENCE_DAYS = 30

# PWTT t-statistic threshold. >1.645 → one-sided p<0.05 (pixel is damaged)
DAMAGE_T_THRESHOLD = 1.645

# Levant AOI — broader than the hex grid to avoid edge effects in S1 acquisition
LEVANT_BBOX = [33.5, 29.0, 38.5, 35.5]  # [west, south, east, north]

# GEE project ID — set via env var or replace here
GEE_PROJECT = os.getenv("GEE_PROJECT", "")


# ── GEE helpers ───────────────────────────────────────────────────────────────

def _init_gee():
    """Authenticate and initialize the Earth Engine Python API."""
    try:
        if GEE_PROJECT:
            ee.Initialize(project=GEE_PROJECT)
        else:
            ee.Initialize()
    except Exception:
        # First run: need to authenticate
        ee.Authenticate()
        if GEE_PROJECT:
            ee.Initialize(project=GEE_PROJECT)
        else:
            ee.Initialize()


def _get_s1_collection(start_date: str, end_date: str, aoi: ee.Geometry) -> ee.ImageCollection:
    """Load Sentinel-1 GRD IW VV images for a date range over the AOI.

    IW (Interferometric Wide Swath) mode is the standard S1 acquisition mode
    over land. VV polarization is most sensitive to structural/volumetric change.
    """
    return (
        ee.ImageCollection("COPERNICUS/S1_GRD")
        .filter(ee.Filter.eq("instrumentMode", "IW"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
        .filter(ee.Filter.eq("orbitProperties_pass", "DESCENDING"))
        .filter(ee.Filter.date(start_date, end_date))
        .filterBounds(aoi)
        .select("VV")
    )


def _pwtt_damage_image(ref_col: ee.ImageCollection,
                        inf_col: ee.ImageCollection) -> ee.Image:
    """Pixel-wise Welch's t-test comparing inference distribution to reference.

    Positive t-statistic: inference mean is LOWER than reference (backscatter dropped).
    Structural damage consistently lowers S1 VV return from urban areas.

    Returns a single-band image named 'damage' containing the t-statistic per pixel.
    """
    ref_mean  = ref_col.mean()
    ref_var   = ref_col.reduce(ee.Reducer.variance())
    ref_count = ref_col.count()

    inf_mean  = inf_col.mean()
    inf_var   = inf_col.reduce(ee.Reducer.variance())
    inf_count = inf_col.count()

    # Welch's t: (ref_mean - inf_mean) / sqrt(ref_var/N_ref + inf_var/N_inf)
    # Positive → inference backscatter is lower than reference → potential damage
    pooled_se = (ref_var.divide(ref_count)
                 .add(inf_var.divide(inf_count))
                 .sqrt())

    t_stat = (ref_mean.subtract(inf_mean)
              .divide(pooled_se.max(ee.Image.constant(1e-6))))

    return t_stat.rename("damage")


def _hexes_to_ee_fc(hex_ids: list[str]) -> ee.FeatureCollection:
    """Convert a list of H3 hex IDs to a GEE FeatureCollection.

    Each hex becomes a polygon Feature with h3_id as a property.
    """
    features = []
    for hid in hex_ids:
        # h3.cell_to_boundary returns [(lat, lng), ...] — GEE wants [lng, lat]
        boundary = h3.cell_to_boundary(hid)
        coords = [[lng, lat] for lat, lng in boundary]
        coords.append(coords[0])  # close the ring
        geom = ee.Geometry.Polygon([coords])
        features.append(ee.Feature(geom, {"h3_id": hid}))
    return ee.FeatureCollection(features)


def _get_hex_ids() -> list[str]:
    """Get the H3 hex IDs that are already in our training data.

    Falls back to polyfilling the Levant bounding box if no training data exists yet.
    """
    # Prefer the hex IDs from the processed training CSV so we only compute
    # damage for hexes the model already knows about
    csv_path = os.path.join(DATA_DIR, "acled_h3_gdelt_firms_weather.csv")
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path, usecols=["h3_id"])
        ids = df["h3_id"].dropna().unique().tolist()
        print(f"  Using {len(ids)} hex IDs from training data")
        return ids

    # Fallback: polyfill the Levant bbox
    west, south, east, north = LEVANT_BBOX
    levant_poly = {
        "type": "Polygon",
        "coordinates": [[[west, south], [east, south],
                          [east, north], [west, north], [west, south]]]
    }
    ids = list(h3.geo_to_cells(levant_poly, H3_RESOLUTION))
    print(f"  Polyfilled {len(ids)} hex IDs over Levant bbox")
    return ids


def _reduce_damage_to_hexes(damage_image: ee.Image,
                             hex_fc: ee.FeatureCollection,
                             scale: int = 100) -> pd.DataFrame:
    """Aggregate per-pixel damage t-statistics to H3 hexes.

    Returns DataFrame with h3_id, damage_mean, damage_fraction.
    scale=100m balances resolution vs compute time. S1 native res is 10m
    but 100m aggregation is sufficient for 36 km² hexes.
    """
    # damage_fraction: fraction of pixels exceeding the damage threshold
    damaged_mask = damage_image.gt(DAMAGE_T_THRESHOLD).rename("damaged_pixel")
    combined = damage_image.addBands(damaged_mask)

    reduced = combined.reduceRegions(
        collection=hex_fc,
        reducer=ee.Reducer.mean(),
        scale=scale,
        crs="EPSG:4326",
    )

    # Pull directly to a Python DataFrame — works for ≤5000 features
    features = reduced.getInfo()["features"]
    rows = []
    for feat in features:
        props = feat["properties"]
        rows.append({
            "h3_id":           props.get("h3_id"),
            "damage_mean":     props.get("damage", np.nan),
            "damage_fraction": props.get("damaged_pixel", np.nan),
        })
    return pd.DataFrame(rows)


# ── Derived features ──────────────────────────────────────────────────────────

def _add_damage_derivatives(df: pd.DataFrame) -> pd.DataFrame:
    """Add velocity and z-score columns to the accumulated damage parquet."""
    df = df.sort_values(["h3_id", "date"])

    # 7-day velocity: how fast is damage increasing?
    df["damage_velocity_7d"] = df.groupby("h3_id")["damage_mean"].transform(
        lambda x: x.diff(7).fillna(0))

    # Z-score vs 30-day rolling baseline per hex
    roll_mean = df.groupby("h3_id")["damage_mean"].transform(
        lambda x: x.rolling(ZSCORE_WINDOW, min_periods=ZSCORE_MIN_PERIODS).mean())
    roll_std = df.groupby("h3_id")["damage_mean"].transform(
        lambda x: x.rolling(ZSCORE_WINDOW, min_periods=ZSCORE_MIN_PERIODS).std())
    df["damage_zscore"] = ((df["damage_mean"] - roll_mean)
                           / roll_std.clip(lower=1e-6)).fillna(0)
    df["damage_zscore"] = df["damage_zscore"].clip(-ZSCORE_CLIP, ZSCORE_CLIP)

    return df


# ── Main ingest ───────────────────────────────────────────────────────────────

def ingest_sar_damage(inference_end_date: str | None = None, backfill: bool = False):
    """Run PWTT for the Levant and append results to the damage parquet.

    Args:
        inference_end_date: ISO date string for end of inference window.
                            Defaults to yesterday (most recent complete day).
        backfill: If True, compute monthly windows from Oct 2023 to today.
    """
    _init_gee()

    aoi = ee.Geometry.Rectangle(LEVANT_BBOX)
    print("Loading reference S1 collection (2022-01-01 → 2023-10-06)...")
    ref_col = _get_s1_collection(REFERENCE_START, REFERENCE_END, aoi)
    ref_count = ref_col.size().getInfo()
    print(f"  Reference images: {ref_count}")
    if ref_count < 10:
        print("  Warning: few reference images — t-test will be noisy")

    hex_ids = _get_hex_ids()
    hex_fc = _hexes_to_ee_fc(hex_ids)

    # Determine which inference windows to compute
    if backfill:
        end = datetime.today() - timedelta(days=1)
        start = datetime(2023, 10, 7)
        # Monthly steps
        dates = []
        cur = start + timedelta(days=30)
        while cur <= end:
            dates.append(cur.strftime("%Y-%m-%d"))
            cur += timedelta(days=30)
    else:
        if inference_end_date is None:
            inference_end_date = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        dates = [inference_end_date]

    # Load existing parquet to avoid recomputing dates already done
    if os.path.exists(OUTPUT):
        existing = pd.read_parquet(OUTPUT)
        done_dates = set(existing["date"].astype(str))
    else:
        existing = pd.DataFrame()
        done_dates = set()

    new_rows = []
    for end_date in dates:
        if end_date in done_dates:
            print(f"  Skip {end_date} (already computed)")
            continue

        start_date = (datetime.strptime(end_date, "%Y-%m-%d")
                      - timedelta(days=INFERENCE_DAYS)).strftime("%Y-%m-%d")
        print(f"Computing damage: inference {start_date} → {end_date}...")

        inf_col = _get_s1_collection(start_date, end_date, aoi)
        inf_count = inf_col.size().getInfo()
        print(f"  Inference images: {inf_count}")
        if inf_count < 2:
            print(f"  Skip {end_date}: not enough S1 images")
            continue

        damage_img = _pwtt_damage_image(ref_col, inf_col)
        batch_df = _reduce_damage_to_hexes(damage_img, hex_fc)
        batch_df["date"] = pd.Timestamp(end_date)
        new_rows.append(batch_df)
        print(f"  {len(batch_df)} hexes scored")

    if not new_rows:
        print("No new dates to compute.")
        return

    new_df = pd.concat(new_rows, ignore_index=True)
    combined = pd.concat([existing, new_df], ignore_index=True)
    combined = combined.drop_duplicates(subset=["h3_id", "date"], keep="last")
    combined = _add_damage_derivatives(combined)

    os.makedirs(DATA_DIR, exist_ok=True)
    combined.to_parquet(OUTPUT, index=False)
    print(f"Saved {len(combined)} rows → {OUTPUT}")
    print(f"  damage_mean range: {combined['damage_mean'].min():.2f} – {combined['damage_mean'].max():.2f}")
    print(f"  damage_fraction range: {combined['damage_fraction'].min():.3f} – {combined['damage_fraction'].max():.3f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sentinel-1 SAR damage ingest")
    parser.add_argument("--date", help="Inference end date (YYYY-MM-DD). Default: yesterday.")
    parser.add_argument("--backfill", action="store_true",
                        help="Compute monthly windows from Oct 2023 to today.")
    args = parser.parse_args()
    ingest_sar_damage(inference_end_date=args.date, backfill=args.backfill)
