"""NOTAMs (Notices to Airmen): airspace closures as onset predictor.

Airspace closures precede military operations by 24-48 hours. Monitoring
FIRs over the Levant provides one of the strongest short-term onset signals.

FIRs monitored:
  OLBB — Beirut FIR (Lebanon)
  LLLL — Tel Aviv FIR (Israel)
  OSDI — Damascus FIR (Syria)
"""
import pandas as pd
import os
import requests
import time
import re

OUTPUT = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "notams_daily.parquet")

# FAA NOTAM API
NOTAM_API = "https://external-api.faa.gov/notamapi/v1/notams"
FIRS = ["OLBB", "LLLL", "OSDI"]

# Military-related keywords in NOTAM text
MILITARY_KEYWORDS = [
    "MIL", "MILITARY", "PROHIBITED", "RESTRICTED", "DANGER AREA",
    "FIRING", "MISSILE", "LIVE FIRE", "AIR DEFENSE", "NO FLY",
    "TEMPORARY RESTRICTED", "COMBAT", "EXERCISE",
]


def fetch_notams_for_fir(fir, api_key=None):
    """Fetch active NOTAMs for a Flight Information Region."""
    if not api_key:
        api_key = os.environ.get("FAA_NOTAM_API_KEY", "")

    if not api_key:
        print(f"  Warning: FAA_NOTAM_API_KEY not set for {fir}")
        return []

    headers = {"client_id": api_key}
    params = {
        "icaoLocation": fir,
        "notamType": "N",  # New NOTAMs
        "sortBy": "notamEffectiveStartDate",
        "sortOrder": "DESC",
        "pageSize": 100,
    }

    rows = []
    try:
        resp = requests.get(NOTAM_API, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        for item in data.get("items", []):
            props = item.get("properties", {})
            text = props.get("coreNOTAMData", {}).get("notam", {}).get("text", "")
            effective = props.get("coreNOTAMData", {}).get("notam", {}).get("effectiveStart", "")
            expire = props.get("coreNOTAMData", {}).get("notam", {}).get("effectiveEnd", "")

            is_military = any(kw.lower() in text.lower() for kw in MILITARY_KEYWORDS)

            if effective:
                rows.append({
                    "date": pd.Timestamp(effective).date(),
                    "fir": fir,
                    "is_military": int(is_military),
                    "text_length": len(text),
                })

    except Exception as e:
        print(f"  Warning: NOTAM API failed for {fir}: {e}")

    return rows


def ingest_notams():
    if os.path.exists(OUTPUT):
        print(f"Cache hit: {OUTPUT}")
        return

    print("Fetching NOTAMs...")
    all_rows = []
    for fir in FIRS:
        print(f"  {fir}...")
        rows = fetch_notams_for_fir(fir)
        all_rows.extend(rows)
        print(f"    {len(rows)} NOTAMs")
        time.sleep(2)

    if not all_rows:
        print("  No NOTAMs fetched (API key required)")
        print("  Get key from: https://notams.aim.faa.gov/notamSearch/")
        print("  Then: export FAA_NOTAM_API_KEY=your_key")
        return

    df = pd.DataFrame(all_rows)
    daily = df.groupby("date").agg(
        notam_active_count=("fir", "size"),
        notam_military_count=("is_military", "sum"),
        notam_firs_affected=("fir", "nunique"),
    ).reset_index()

    daily["notam_is_military"] = (daily["notam_military_count"] > 0).astype(int)

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    daily.to_parquet(OUTPUT, index=False)
    print(f"  Saved {len(daily)} rows to {OUTPUT}")


if __name__ == "__main__":
    ingest_notams()
