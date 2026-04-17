import pandas as pd
import os

RAMADAN_DATES = [
    ("2020-04-24", "2020-05-23"),
    ("2021-04-13", "2021-05-12"),
    ("2022-04-02", "2022-05-01"),
    ("2023-03-23", "2023-04-20"),
    ("2024-03-11", "2024-04-09"),
    ("2025-03-01", "2025-03-29"),
]

JERUSALEM_DAY = ["2020-05-22", "2021-05-10", "2022-05-29", "2023-05-18", "2024-06-05", "2025-05-26"]

ELECTION_DATES = ["2021-03-23", "2022-11-01", "2022-10-30"]  # Israel + Lebanon elections

def ingest_calendar(output_path="data/processed/calendar_daily.parquet"):
    if os.path.exists(output_path):
        print(f"Cache hit: {output_path}")
        return

    # Need one row per day from 2020-2025
    # - Create list of dates so every other feature can be attached to it
    dates = pd.date_range("2020-01-01", "2025-12-31")
    df = pd.DataFrame({"date": dates.date})

    # Need a list of individual date strings for Ramadan
    # - Since it's ~30 days, build list automatically instead of manually
    ramadan_flat = []
    for start, end in RAMADAN_DATES:
        ramadan_flat += pd.date_range(start, end).strftime("%Y-%m-%d").tolist()

    # For each date in DataFrame, we need True/False for these events
    # - Build a binary column for both events
    df["is_ramadan"] = df["date"].astype(str).isin(ramadan_flat).astype(int)
    df["is_jerusalem_day"] = df["date"].astype(str).isin(JERUSALEM_DAY).astype(int)

    # Need to account for the entire election window
    # - Build a +/- 90 day window before and after election day, add binary column for those days
    election_window = []
    for d in ELECTION_DATES:
        center = pd.Timestamp(d)
        window = pd.date_range(center - pd.Timedelta(days=90), center + pd.Timedelta(days=90))
        election_window += window.strftime("%Y-%m-%d").tolist()
    df["is_election_window"] = df["date"].astype(str).isin(election_window).astype(int)

    # Save file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_parquet(output_path, index=False)
    print(f"Saved {len(df)} rows to {output_path}")  

if __name__ == "__main__":
    ingest_calendar()
