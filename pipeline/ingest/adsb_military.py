"""OpenSky ADS-B: military ISR aircraft tracking + GNSS jamming detection.

ISR (Intelligence, Surveillance, Reconnaissance) aircraft surges precede
strikes by hours. GPS/GNSS jamming (detectable via NACp degradation in
ADS-B data) indicates electronic warfare activation — a strong onset signal.

Requires: OpenSky account (free, 8000 credits/day for registered users).
"""
import pandas as pd
import numpy as np
import os
import requests
from datetime import datetime, timedelta

OUTPUT = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "adsb_daily.parquet")

# Levant bounding box
LAT_MIN, LAT_MAX = 32.5, 34.8
LON_MIN, LON_MAX = 34.5, 37.5

# OpenSky REST API
OPENSKY_URL = "https://opensky-network.org/api"

# Known military aircraft type codes (partial list)
MILITARY_TYPES = {
    "C130", "C17", "KC135", "P8", "RC135", "E3", "E2",
    "F15", "F16", "F35", "B52",
    "HRON", "GLBX",  # Global Hawk, RQ-4
}


def fetch_flights_in_bbox(start_ts, end_ts, username=None, password=None):
    """Fetch flights within Levant bbox from OpenSky."""
    if not username:
        username = os.environ.get("OPENSKY_USER", "")
        password = os.environ.get("OPENSKY_PASS", "")

    params = {
        "lamin": LAT_MIN, "lamax": LAT_MAX,
        "lomin": LON_MIN, "lomax": LON_MAX,
        "begin": int(start_ts),
        "end": int(end_ts),
    }

    auth = (username, password) if username else None

    try:
        resp = requests.get(f"{OPENSKY_URL}/flights/all",
                           params=params, auth=auth, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return []


def detect_gnss_jamming(states_data):
    """Detect GPS jamming from NACp (Navigation Accuracy Category - Position).

    Normal NACp is 8-11. Values < 5 indicate degraded GPS accuracy,
    which often means electronic warfare jamming in conflict zones.
    """
    if not states_data:
        return 0, 0

    low_nacp_count = 0
    total_count = len(states_data)

    for state in states_data:
        # OpenSky state vector: position 16 is NACp (if available)
        if len(state) > 16 and state[16] is not None:
            nacp = state[16]
            if nacp < 5:
                low_nacp_count += 1

    jamming_ratio = low_nacp_count / max(total_count, 1)
    return low_nacp_count, jamming_ratio


def fetch_current_states():
    """Fetch current aircraft states in Levant bbox."""
    username = os.environ.get("OPENSKY_USER", "")
    password = os.environ.get("OPENSKY_PASS", "")
    auth = (username, password) if username else None

    params = {
        "lamin": LAT_MIN, "lamax": LAT_MAX,
        "lomin": LON_MIN, "lomax": LON_MAX,
    }

    try:
        resp = requests.get(f"{OPENSKY_URL}/states/all",
                           params=params, auth=auth, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("states", [])
    except Exception as e:
        print(f"  Warning: OpenSky API failed: {e}")
        return []


def ingest_adsb():
    if os.path.exists(OUTPUT):
        print(f"Cache hit: {OUTPUT}")
        return

    print("Fetching OpenSky ADS-B data...")

    username = os.environ.get("OPENSKY_USER", "")
    if not username:
        print("  OPENSKY_USER and OPENSKY_PASS not set.")
        print("  Register free at: https://opensky-network.org/index.php/member/register")
        print("  Then: export OPENSKY_USER=xxx OPENSKY_PASS=yyy")
        print("  Generating placeholder data for pipeline integration...")

        # Placeholder: 0 values so pipeline works
        dates = pd.date_range("2020-01-01", "2024-12-10").date
        df = pd.DataFrame({
            "date": dates,
            "military_flight_count": 0,
            "gnss_jamming_count": 0,
            "gnss_jamming_ratio": 0.0,
            "total_aircraft_count": 0,
        })

        os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
        df.to_parquet(OUTPUT, index=False)
        print(f"  Saved placeholder: {len(df)} rows to {OUTPUT}")
        return

    # Fetch current snapshot
    states = fetch_current_states() or []
    print(f"  Current aircraft in Levant bbox: {len(states)}")

    jamming_count, jamming_ratio = detect_gnss_jamming(states)
    print(f"  GNSS jamming indicators: {jamming_count} low-NACp ({jamming_ratio:.1%})")

    # For historical data, would need to query day-by-day (expensive)
    # For now, save current snapshot as proof of concept
    today = datetime.utcnow().date()
    df = pd.DataFrame([{
        "date": today,
        "military_flight_count": 0,  # Need callsign classification
        "gnss_jamming_count": jamming_count,
        "gnss_jamming_ratio": jamming_ratio,
        "total_aircraft_count": len(states),
    }])

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    df.to_parquet(OUTPUT, index=False)
    print(f"  Saved {len(df)} rows to {OUTPUT}")


if __name__ == "__main__":
    ingest_adsb()
