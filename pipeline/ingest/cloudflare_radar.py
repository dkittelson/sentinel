"""Cloudflare Radar: netflow traffic anomalies per country.

Uses the /radar/netflows/timeseries endpoint (confirmed working).
Also queries /radar/traffic_anomalies for detected outage events.
"""
import pandas as pd
import numpy as np
import os
import requests
import time
from datetime import datetime, timedelta

OUTPUT = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "cloudflare_daily.parquet")
COUNTRIES = ["IL", "LB", "SY"]

# Cloudflare Radar limits dateRange to specific windows
# We'll query in 12-week chunks
CHUNK_WEEKS = 12


def fetch_netflows(country, token, start_date, end_date):
    """Fetch netflow timeseries for a country in chunks."""
    headers = {"Authorization": f"Bearer {token}"}
    all_data = []

    current = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)

    while current < end:
        chunk_end = min(current + pd.Timedelta(weeks=CHUNK_WEEKS), end)
        params = {
            "location": country,
            "dateStart": current.strftime("%Y-%m-%dT00:00:00Z"),
            "dateEnd": chunk_end.strftime("%Y-%m-%dT00:00:00Z"),
            "aggInterval": "1d",
        }

        try:
            resp = requests.get(
                "https://api.cloudflare.com/client/v4/radar/netflows/timeseries",
                headers=headers, params=params, timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json().get("result", {}).get("serie_0", {})
                timestamps = data.get("timestamps", [])
                values = data.get("values", [])
                for ts, val in zip(timestamps, values):
                    all_data.append({
                        "date": pd.Timestamp(ts).date(),
                        f"cf_netflow_{country.lower()}": float(val),
                    })
        except Exception as e:
            print(f"    Warning: chunk {current.date()} failed: {e}")

        current = chunk_end
        time.sleep(1)

    return all_data


def fetch_anomalies(country, token, start_date, end_date):
    """Fetch traffic anomaly events for a country."""
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "location": country,
        "dateStart": start_date,
        "dateEnd": end_date,
    }
    try:
        resp = requests.get(
            "https://api.cloudflare.com/client/v4/radar/traffic_anomalies",
            headers=headers, params=params, timeout=30,
        )
        if resp.status_code == 200:
            anomalies = resp.json().get("result", {}).get("trafficAnomalies", [])
            return len(anomalies)
    except Exception:
        pass
    return 0


def ingest_cloudflare():
    if os.path.exists(OUTPUT):
        print(f"Cache hit: {OUTPUT}")
        return

    token = os.environ.get("CLOUDFLARE_API_TOKEN", "")
    if not token:
        print("CLOUDFLARE_API_TOKEN not set")
        return

    print("Fetching Cloudflare Radar data...")

    # Cloudflare Radar free tier only has recent data (~12 weeks)
    # For historical, we'll get what we can and fill the rest
    all_rows = []
    for country in COUNTRIES:
        print(f"  {country}...")
        rows = fetch_netflows(country, token, "2025-01-01", "2026-04-18")
        all_rows.extend(rows)
        n_anomalies = fetch_anomalies(country, token, "2025-01-01", "2026-04-18")
        print(f"    {len(rows)} data points, {n_anomalies} anomalies")
        time.sleep(2)

    if not all_rows:
        print("  No data fetched")
        return

    df = pd.DataFrame(all_rows)
    # Pivot so each country is a column
    daily = df.groupby("date").first().reset_index()

    # Compute anomaly scores
    for country in COUNTRIES:
        col = f"cf_netflow_{country.lower()}"
        if col in daily.columns:
            roll30 = daily[col].rolling(30, min_periods=7).mean()
            daily[f"cf_anomaly_{country.lower()}"] = daily[col] - roll30

    daily = daily.fillna(0)

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    daily.to_parquet(OUTPUT, index=False)
    print(f"  Saved {len(daily)} rows to {OUTPUT}")


if __name__ == "__main__":
    ingest_cloudflare()
