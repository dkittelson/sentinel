"""UCDP Georeferenced Event Dataset (GED) ingest for the Levant.

UCDP GED v25.1 covers organized violence globally at the event level.
Three event categories:
  - State-based conflict (battles between governments and armed groups)
  - Non-state conflict (armed group vs armed group)
  - One-sided violence (attacks on civilians)

Unlike ACLED (which uses a proprietary license and has commercial restrictions),
UCDP GED is CC BY 4.0 (full commercial reuse) and provides an independent
ground-truth source for conflict validation and model diversification.

Reference: https://ucdp.uu.se/downloads/ged/ged251.pdf
API docs:  https://ucdp.uu.se/apidocs/

Output: pipeline/data/processed/ucdp_hex_daily.parquet
Columns:
  h3_id                   — H3 resolution-6 hex ID
  date                    — event date
  ucdp_event_count        — events in hex that day
  ucdp_fatalities_best    — best fatality estimate (UCDP "best" field)
  ucdp_fatalities_high    — high fatality estimate
  ucdp_state_based        — count of state-based conflict events
  ucdp_nonstate           — count of non-state conflict events
  ucdp_onesided           — count of one-sided violence events
  ucdp_acled_agree        — 1 if ucdp_event_count > 0 and ACLED dangerous_count > 0
                            on same hex-day (cross-source validation; computed in split_data)

Note on publication lag: UCDP "candidate" events (provisional) are updated monthly
with ~30-day lag. The GED REST API returns candidate events for recent dates.
Enforce a 30-day lag in split_data.py for the ucdp_* columns.

Usage:
  python pipeline/ingest/ucdp_ged.py               # current year + last 2 years
  python pipeline/ingest/ucdp_ged.py --backfill     # all data from 2020-01-01
  python pipeline/ingest/ucdp_ged.py --year 2023    # specific year
"""

import argparse
import os
import sys
import time

import h3
import numpy as np
import pandas as pd
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ml.config import H3_RESOLUTION, START_DATE, END_DATE

OUTPUT   = os.path.join(os.path.dirname(__file__), "..", "data", "processed",
                         "ucdp_hex_daily.parquet")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")

# UCDP REST API v3 (CC BY 4.0)
API_BASE = "https://ucdpapi.pcr.uu.se/api"
PAGE_SIZE = 1000  # max events per page

# Levant bbox filter
LAT_MIN, LAT_MAX = 29.0, 35.5
LON_MIN, LON_MAX = 33.5, 38.5

# UCDP type_of_violence → human-readable
VIOLENCE_TYPES = {1: "state_based", 2: "nonstate", 3: "onesided"}


# ── API helpers ───────────────────────────────────────────────────────────────

def _fetch_page(year: int, page: int, retries: int = 3) -> dict | None:
    """Fetch one page of UCDP GED events for a given year."""
    url = f"{API_BASE}/gedevents/25.1"
    params = {
        "pagesize": PAGE_SIZE,
        "page": page,
        "year": year,
        "type_of_violence": "1,2,3",  # all three categories
    }
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=60)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 404:
                return None  # year not available
            print(f"    HTTP {resp.status_code} (attempt {attempt + 1})")
        except Exception as exc:
            print(f"    Request error: {exc} (attempt {attempt + 1})")
        time.sleep(2 ** attempt)
    return None


def _fetch_year(year: int) -> pd.DataFrame:
    """Fetch all UCDP GED events for a year via paginated API."""
    print(f"  Fetching UCDP GED year {year}...")
    all_rows = []
    page = 1

    while True:
        data = _fetch_page(year, page)
        if data is None:
            break

        events = data.get("Result", [])
        if not events:
            break

        for evt in events:
            lat = evt.get("latitude")
            lon = evt.get("longitude")
            if lat is None or lon is None:
                continue
            try:
                lat, lon = float(lat), float(lon)
            except (TypeError, ValueError):
                continue

            # Levant bbox filter
            if not (LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX):
                continue

            date_str = evt.get("date_start", "")
            if not date_str:
                continue
            try:
                date = pd.Timestamp(date_str[:10])
            except Exception:
                continue

            all_rows.append({
                "date":             date,
                "lat":              lat,
                "lon":              lon,
                "deaths_best":      int(evt.get("best", 0) or 0),
                "deaths_high":      int(evt.get("high", 0) or 0),
                "type_of_violence": int(evt.get("type_of_violence", 0) or 0),
            })

        total_pages = data.get("TotalPages", 1)
        print(f"    Page {page}/{total_pages}: {len(events)} events "
              f"({len(all_rows)} Levant so far)")
        if page >= total_pages:
            break
        page += 1
        time.sleep(0.5)  # be polite to the API

    return pd.DataFrame(all_rows) if all_rows else pd.DataFrame(
        columns=["date", "lat", "lon", "deaths_best", "deaths_high", "type_of_violence"])


def _aggregate_to_hex(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate UCDP events to hex-day level."""
    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    df["h3_id"] = [h3.latlng_to_cell(lat, lon, H3_RESOLUTION)
                   for lat, lon in zip(df["lat"], df["lon"])]

    agg = df.groupby(["h3_id", "date"]).agg(
        ucdp_event_count   = ("deaths_best", "count"),
        ucdp_fatalities_best = ("deaths_best", "sum"),
        ucdp_fatalities_high = ("deaths_high", "sum"),
    ).reset_index()

    for vtype, col in [(1, "ucdp_state_based"), (2, "ucdp_nonstate"), (3, "ucdp_onesided")]:
        counts = (df[df["type_of_violence"] == vtype]
                  .groupby(["h3_id", "date"]).size().rename(col))
        agg = agg.merge(counts.reset_index(), on=["h3_id", "date"], how="left")
        agg[col] = agg[col].fillna(0).astype(int)

    return agg


# ── Main ingest ───────────────────────────────────────────────────────────────

def ingest_ucdp(year: int | None = None, backfill: bool = False):
    """Fetch UCDP GED events for the Levant and append to parquet.

    Args:
        year:     Specific year to fetch. Defaults to current year + 2 prior years.
        backfill: If True, fetch all years from 2020 to current year.
    """
    current_year = pd.Timestamp.today().year

    if backfill:
        years = list(range(int(START_DATE[:4]), current_year + 1))
    elif year is not None:
        years = [year]
    else:
        years = [current_year - 1, current_year]

    if os.path.exists(OUTPUT):
        existing = pd.read_parquet(OUTPUT)
        done_years = set(existing["date"].dt.year.unique())
    else:
        existing = pd.DataFrame()
        done_years = set()

    new_chunks = []
    for yr in years:
        if yr in done_years and not backfill:
            print(f"  Skip {yr} (cached)")
            continue

        year_df = _fetch_year(yr)
        if year_df.empty:
            print(f"  No Levant events for {yr}")
            continue

        hex_df = _aggregate_to_hex(year_df)
        print(f"  {yr}: {len(year_df)} events → {len(hex_df)} hex-day rows")
        new_chunks.append(hex_df)

    if not new_chunks:
        print("No new data.")
        return

    new_df = pd.concat(new_chunks, ignore_index=True)

    # Drop existing rows for the years we just re-fetched (in case of backfill re-runs)
    if not existing.empty and backfill:
        existing = existing[~existing["date"].dt.year.isin(years)]

    combined = pd.concat([existing, new_df], ignore_index=True)
    combined = combined.drop_duplicates(subset=["h3_id", "date"], keep="last")
    combined = combined.sort_values(["h3_id", "date"]).reset_index(drop=True)

    os.makedirs(DATA_DIR, exist_ok=True)
    combined.to_parquet(OUTPUT, index=False)
    print(f"Saved {len(combined)} rows → {OUTPUT}")
    print(f"  Fatality range: {combined['ucdp_fatalities_best'].min()} – "
          f"{combined['ucdp_fatalities_best'].max()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UCDP GED ingest for Levant")
    parser.add_argument("--year", type=int, help="Specific year to fetch.")
    parser.add_argument("--backfill", action="store_true",
                        help="Fetch all years from 2020 to current year.")
    args = parser.parse_args()
    ingest_ucdp(year=args.year, backfill=args.backfill)
