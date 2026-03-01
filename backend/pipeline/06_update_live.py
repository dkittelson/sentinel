"""
Step 6: Live Data Refresh Pipeline
====================================
Incrementally extends the processed feature table with new ACLED/GDELT/FIRMS data.

Instead of re-running the full pipeline (hours of GDELT downloads), this script:
1. Re-runs ACLED preprocessing (01) on the latest raw CSV → extends acled_h3.csv
2. Fetches only MISSING GDELT days (incremental) → extends acled_h3_gdelt.csv
3. Fetches only MISSING FIRMS days (incremental) → extends acled_h3_gdelt_firms.csv

The backtest engine and /hexes live endpoint auto-detect the updated CSV.

Usage:
    cd sentinel && python backend/pipeline/06_update_live.py
"""

import os
import sys
import subprocess
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
os.chdir(ROOT)

ACLED_H3_PATH       = "data/processed/acled_h3.csv"
GDELT_MERGED_PATH   = "data/processed/acled_h3_gdelt.csv"
FIRMS_MERGED_PATH   = "data/processed/acled_h3_gdelt_firms.csv"


def get_current_max_date(path: str) -> pd.Timestamp | None:
    """Get the latest event_date in a processed CSV."""
    if not os.path.exists(path):
        return None
    # Read just enough to find the max date efficiently
    df = pd.read_csv(path, usecols=["event_date"])
    df["event_date"] = pd.to_datetime(df["event_date"])
    return df["event_date"].max()


def step1_preprocess_acled():
    """Re-run ACLED preprocessing. This is the foundation — must run first."""
    print("\n" + "=" * 60)
    print("STEP 1: Re-running ACLED preprocessing...")
    print("=" * 60)
    result = subprocess.run(
        [sys.executable, "backend/pipeline/01_preprocess_acled.py"],
        cwd=ROOT,
    )
    if result.returncode != 0:
        print("ERROR: ACLED preprocessing failed!")
        sys.exit(1)
    print("✓ ACLED preprocessing complete")


def step2_ingest_gdelt():
    """Re-run GDELT ingestion. Uses cache so previously fetched days are instant."""
    print("\n" + "=" * 60)
    print("STEP 2: Running GDELT ingestion (cached days are instant)...")
    print("=" * 60)
    result = subprocess.run(
        [sys.executable, "backend/pipeline/03_ingest_gdelt.py"],
        cwd=ROOT,
    )
    if result.returncode != 0:
        print("WARNING: GDELT ingestion failed — using ACLED-only features")
        # Copy acled_h3.csv as the gdelt merged file with zero GDELT columns
        import shutil
        df = pd.read_csv(ACLED_H3_PATH)
        for col in ["gdelt_event_count", "gdelt_avg_tone", "gdelt_min_goldstein",
                     "gdelt_avg_goldstein", "gdelt_num_articles", "gdelt_hostility",
                     "neighbor_gdelt_hostility_avg"]:
            df[col] = 0
        df.to_csv(GDELT_MERGED_PATH, index=False)
    print("✓ GDELT ingestion complete")


def step3_ingest_firms():
    """Re-run FIRMS ingestion. Fetches in 5-day chunks."""
    print("\n" + "=" * 60)
    print("STEP 3: Running FIRMS ingestion...")
    print("=" * 60)
    result = subprocess.run(
        [sys.executable, "backend/pipeline/04_ingest_firms.py"],
        cwd=ROOT,
    )
    if result.returncode != 0:
        print("WARNING: FIRMS ingestion failed — using ACLED+GDELT features only")
        df = pd.read_csv(GDELT_MERGED_PATH)
        for col in ["firms_hotspot_count", "firms_avg_frp", "firms_max_frp",
                     "firms_spike", "neighbor_firms_spike_sum"]:
            df[col] = 0
        df.to_csv(FIRMS_MERGED_PATH, index=False)
    print("✓ FIRMS ingestion complete")


def report():
    """Print summary of the updated data."""
    print("\n" + "=" * 60)
    print("PIPELINE REFRESH COMPLETE")
    print("=" * 60)
    for label, path in [
        ("ACLED H3", ACLED_H3_PATH),
        ("+ GDELT",  GDELT_MERGED_PATH),
        ("+ FIRMS",  FIRMS_MERGED_PATH),
    ]:
        if os.path.exists(path):
            df = pd.read_csv(path, usecols=["event_date", "h3_id"])
            df["event_date"] = pd.to_datetime(df["event_date"])
            print(f"  {label:12s}: {len(df):>10,} rows  |  "
                  f"{df['h3_id'].nunique():,} hexes  |  "
                  f"{df['event_date'].min().date()} → {df['event_date'].max().date()}")
    print("\nThe backtest engine and /hexes live endpoint will auto-detect new data.")
    print("Restart the backend server to clear cached data:\n"
          "  kill $(lsof -ti :8000) && uvicorn backend.main:app --port 8000")


if __name__ == "__main__":
    # Show current state
    current_max = get_current_max_date(FIRMS_MERGED_PATH)
    if current_max:
        print(f"Current processed data ends at: {current_max.date()}")
    else:
        print("No processed data found — running full pipeline")

    step1_preprocess_acled()
    step2_ingest_gdelt()
    step3_ingest_firms()
    report()
