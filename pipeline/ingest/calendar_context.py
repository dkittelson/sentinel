"""Calendar/context features: religious events, political windows, cyclical time.

Calendar features don't cause conflict but modulate timing. Ramadan, Jerusalem
Day, and Nakba Day are associated with elevated tension in the Levant.
"""
import pandas as pd
import numpy as np
import os

# ── Religious / Cultural Events ───────────────────────────────
RAMADAN_DATES = [
    ("2020-04-24", "2020-05-23"),
    ("2021-04-13", "2021-05-12"),
    ("2022-04-02", "2022-05-01"),
    ("2023-03-23", "2023-04-20"),
    ("2024-03-11", "2024-04-09"),
    ("2025-03-01", "2025-03-29"),
]

JERUSALEM_DAY = ["2020-05-22", "2021-05-10", "2022-05-29", "2023-05-18", "2024-06-05", "2025-05-26"]

NAKBA_DAY = ["2020-05-15", "2021-05-15", "2022-05-15", "2023-05-15", "2024-05-15", "2025-05-15"]

# Ashura (Shia commemoration — significant in Lebanon/Hezbollah context)
ASHURA_DATES = ["2020-08-30", "2021-08-19", "2022-08-08", "2023-07-28", "2024-07-17", "2025-07-06"]

# Yom Kippur (Israel — military readiness historically affected)
YOM_KIPPUR = ["2020-09-28", "2021-09-16", "2022-10-05", "2023-09-25", "2024-10-12", "2025-10-02"]

# ── Political Windows ────────────────────────────────────────
# Israel + Lebanon elections (±90 day windows)
ELECTION_DATES = [
    "2021-03-23",  # Israel
    "2022-05-15",  # Lebanon parliamentary
    "2022-11-01",  # Israel
]


def _build_window(dates, window_days=3):
    """Build flat date list with ±window around each date."""
    flat = []
    for d in dates:
        center = pd.Timestamp(d)
        flat += pd.date_range(
            center - pd.Timedelta(days=window_days),
            center + pd.Timedelta(days=window_days)
        ).strftime("%Y-%m-%d").tolist()
    return flat


def ingest_calendar(output_path="data/processed/calendar_daily.parquet"):
    if os.path.exists(output_path):
        print(f"Cache hit: {output_path}")
        return

    dates = pd.date_range("2020-01-01", "2025-12-31")
    df = pd.DataFrame({"date": dates.date})
    date_str = df["date"].astype(str)

    # ── Ramadan (full duration) ───────────────────────────────
    ramadan_flat = []
    for start, end in RAMADAN_DATES:
        ramadan_flat += pd.date_range(start, end).strftime("%Y-%m-%d").tolist()
    df["is_ramadan"] = date_str.isin(ramadan_flat).astype(int)

    # ── Single-day events (with ±3 day window for spillover) ──
    df["is_jerusalem_day"] = date_str.isin(_build_window(JERUSALEM_DAY, 3)).astype(int)
    df["is_nakba_day"] = date_str.isin(_build_window(NAKBA_DAY, 3)).astype(int)
    df["is_ashura"] = date_str.isin(_build_window(ASHURA_DATES, 2)).astype(int)
    df["is_yom_kippur"] = date_str.isin(_build_window(YOM_KIPPUR, 1)).astype(int)

    # ── Election window (±90 days) ────────────────────────────
    election_window = []
    for d in ELECTION_DATES:
        center = pd.Timestamp(d)
        election_window += pd.date_range(
            center - pd.Timedelta(days=90), center + pd.Timedelta(days=90)
        ).strftime("%Y-%m-%d").tolist()
    df["is_election_window"] = date_str.isin(election_window).astype(int)

    # ── Cyclical time encoding ────────────────────────────────
    # Day of week (sin/cos for cyclical nature)
    dow = dates.dayofweek  # 0=Monday, 4=Friday
    df["day_sin"] = np.sin(2 * np.pi * dow / 7).round(4)
    df["day_cos"] = np.cos(2 * np.pi * dow / 7).round(4)

    # Friday flag (weekly protest day in many MENA countries)
    df["is_friday"] = (dow == 4).astype(int)

    # Month of year (seasonal patterns)
    moy = dates.month
    df["month_sin"] = np.sin(2 * np.pi * moy / 12).round(4)
    df["month_cos"] = np.cos(2 * np.pi * moy / 12).round(4)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_parquet(output_path, index=False)
    print(f"Saved {len(df)} rows, {len(df.columns)} cols to {output_path}")


if __name__ == "__main__":
    ingest_calendar()
