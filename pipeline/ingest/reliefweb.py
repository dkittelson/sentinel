"""ReliefWeb API: UNIFIL/humanitarian report volume and escalation signals.

UN reports provide official escalation language. UNIFIL Blue Line incident
reports are a direct onset indicator for Lebanon-Israel border.
"""
import pandas as pd
import os
import requests
import time

OUTPUT = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "reliefweb_daily.parquet")
API_URL = "https://api.reliefweb.int/v1/reports"

COUNTRIES = ["Lebanon", "Syria", "Israel"]
ESCALATION_KEYWORDS = [
    "escalation", "shelling", "airstrike", "ceasefire violation",
    "rocket", "missile", "incursion", "military operation",
    "displacement", "evacuation", "casualties", "UNIFIL",
]


def fetch_reliefweb_reports(country, start="2020-01-01", end="2024-12-10"):
    """Fetch daily report counts from ReliefWeb for a country."""
    rows = []
    offset = 0
    limit = 1000

    while True:
        params = {
            "appname": "sentinel-conflict-monitor",
            "filter[field]": "country.name",
            "filter[value]": country,
            "filter[operator]": "AND",
            "fields[include][]": ["date.created", "title"],
            "sort[]": "date.created:asc",
            "limit": limit,
            "offset": offset,
        }

        # Use date range filter
        payload = {
            "filter": {
                "operator": "AND",
                "conditions": [
                    {"field": "country.name", "value": country},
                    {"field": "date.created", "value": {"from": start, "to": end}},
                ]
            },
            "fields": {"include": ["date.created", "title"]},
            "sort": ["date.created:asc"],
            "limit": limit,
            "offset": offset,
        }

        try:
            resp = requests.post(API_URL, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("data", [])

            for item in items:
                fields = item.get("fields", {})
                created = fields.get("date", {}).get("created", "")
                title = fields.get("title", "")
                if created:
                    date = pd.Timestamp(created).date()
                    has_escalation = any(kw.lower() in title.lower() for kw in ESCALATION_KEYWORDS)
                    rows.append({"date": date, "country": country, "escalation": int(has_escalation)})

            if len(items) < limit:
                break
            offset += limit
            time.sleep(1)

        except Exception as e:
            print(f"  Warning: ReliefWeb API failed for {country} at offset {offset}: {e}")
            break

    return rows


def ingest_reliefweb():
    if os.path.exists(OUTPUT):
        print(f"Cache hit: {OUTPUT}")
        return

    print("Fetching ReliefWeb data...")
    all_rows = []
    for country in COUNTRIES:
        print(f"  {country}...")
        rows = fetch_reliefweb_reports(country)
        all_rows.extend(rows)
        print(f"    {len(rows)} reports")

    if not all_rows:
        print("  No data fetched")
        return

    df = pd.DataFrame(all_rows)
    df["date"] = pd.to_datetime(df["date"])

    # Aggregate per date (across all countries)
    daily = df.groupby("date").agg(
        reliefweb_report_count=("country", "size"),
        reliefweb_escalation_count=("escalation", "sum"),
    ).reset_index()

    # Add rolling features
    daily = daily.sort_values("date")
    daily["reliefweb_report_roll7d"] = daily["reliefweb_report_count"].rolling(7, min_periods=1).mean()
    daily["reliefweb_escalation_flag"] = (daily["reliefweb_escalation_count"] > 0).astype(int)
    daily["date"] = daily["date"].dt.date

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    daily.to_parquet(OUTPUT, index=False)
    print(f"  Saved {len(daily)} rows to {OUTPUT}")


if __name__ == "__main__":
    ingest_reliefweb()
