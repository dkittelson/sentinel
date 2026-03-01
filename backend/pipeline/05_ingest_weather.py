"""
Step 5: Open-Meteo Weather Feature Ingestion
Uses ERA5 reanalysis (free, no API key) to build weekly climate features per H3 hex.

Climate-conflict link in the Levant is well-documented:
  - Heat stress spikes → economic/social tension
  - Precipitation deficits (drought) → food insecurity → unrest
  - Temperature anomaly → captures unusual conditions beyond seasonal baseline

Strategy: query a 4x5 lat/lon grid (20 points) covering the bounding box,
then assign each hex to its nearest grid point.

Output: data/processed/acled_h3_gdelt_firms_weather.csv
"""

import pandas as pd
import numpy as np
import requests
import h3
import time
from tqdm import tqdm

# ── Config ────────────────────────────────────────────────────────────────────
IN_PATH  = "data/processed/acled_h3_gdelt_firms.csv"
OUT_PATH = "data/processed/acled_h3_gdelt_firms_weather.csv"

H3_RESOLUTION = 6

# Levant bounding box
LAT_MIN, LAT_MAX = 29.5, 37.5
LON_MIN, LON_MAX = 33.5, 42.5

# 4x5 grid = 20 ERA5 query points covering the region
GRID_LATS = np.linspace(30.0, 37.0, 4)   # 30, 32.3, 34.7, 37
GRID_LONS = np.linspace(34.0, 42.0, 5)   # 34, 36, 38, 40, 42

# Open-Meteo API (free, no key, ERA5 historical archive)
OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"

# ── Load base table ───────────────────────────────────────────────────────────
print(f"Loading {IN_PATH}...")
df = pd.read_csv(IN_PATH, parse_dates=["week"])
df = df.sort_values(["h3_id", "week"]).reset_index(drop=True)
print(f"  {len(df):,} hex-week rows")

start_date = df["week"].min().strftime("%Y-%m-%d")
end_date   = (df["week"].max() + pd.Timedelta(weeks=1)).strftime("%Y-%m-%d")
print(f"  Date range: {start_date} to {end_date}")

# ── Build grid of weather query points ────────────────────────────────────────
grid_points = [(lat, lon) for lat in GRID_LATS for lon in GRID_LONS]
print(f"\nQuerying Open-Meteo ERA5 for {len(grid_points)} grid points...")

def fetch_weather(lat, lon, start, end):
    """Fetch daily ERA5 weather for a single point, splitting into yearly chunks to avoid timeouts."""
    all_chunks = []
    years = pd.date_range(start=start, end=end, freq="YS")
    dates = [d.strftime("%Y-%m-%d") for d in years] + [end]

    for i in range(len(dates) - 1):
        params = {
            "latitude":   round(lat, 2),
            "longitude":  round(lon, 2),
            "start_date": dates[i],
            "end_date":   dates[i + 1],
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
            "timezone": "UTC",
        }
        for attempt in range(4):
            try:
                time.sleep(0.8 + attempt * 1.5)
                r = requests.get(OPEN_METEO_URL, params=params, timeout=30)
                if r.status_code == 200:
                    data = r.json()
                    if "daily" not in data:
                        break
                    daily = data["daily"]
                    chunk = pd.DataFrame({
                        "date":     pd.to_datetime(daily["time"]),
                        "temp_max": daily["temperature_2m_max"],
                        "temp_min": daily["temperature_2m_min"],
                        "precip":   daily["precipitation_sum"],
                        "grid_lat": lat,
                        "grid_lon": lon,
                    })
                    all_chunks.append(chunk)
                    break
            except Exception:
                pass

    if all_chunks:
        return pd.concat(all_chunks, ignore_index=True)
    print(f"  Warning: failed ({lat:.1f}, {lon:.1f})")
    return pd.DataFrame()

all_weather = []
for lat, lon in tqdm(grid_points, desc="  ERA5 download"):
    w = fetch_weather(lat, lon, start_date, end_date)
    if not w.empty:
        all_weather.append(w)

weather_daily = pd.concat(all_weather, ignore_index=True)
print(f"  Total daily records: {len(weather_daily):,}")

# ── Compute climate anomalies ─────────────────────────────────────────────────
print("Computing temperature and precipitation anomalies...")

weather_daily["month"] = weather_daily["date"].dt.month

# Monthly baseline per grid point (multi-year average for same calendar month)
monthly_baseline = weather_daily.groupby(["grid_lat", "grid_lon", "month"]).agg(
    baseline_temp  = ("temp_max", "mean"),
    baseline_precip = ("precip", "mean"),
    p20_precip     = ("precip", lambda x: x.quantile(0.20)),  # drought threshold
).reset_index()

weather_daily = weather_daily.merge(monthly_baseline, on=["grid_lat", "grid_lon", "month"], how="left")
weather_daily["temp_anomaly"]  = weather_daily["temp_max"]  - weather_daily["baseline_temp"]
weather_daily["precip_anomaly"] = weather_daily["precip"] - weather_daily["baseline_precip"]
weather_daily["drought_day"]   = (weather_daily["precip"] <= weather_daily["p20_precip"]).astype(int)

# ── Weekly aggregation per grid point ─────────────────────────────────────────
print("Aggregating to weekly per grid point...")

weather_daily["week"] = weather_daily["date"].dt.to_period("W").dt.start_time

weather_weekly = weather_daily.groupby(["grid_lat", "grid_lon", "week"]).agg(
    weather_temp_max       = ("temp_max",       "max"),
    weather_temp_mean      = ("temp_max",       "mean"),
    weather_temp_anomaly   = ("temp_anomaly",   "mean"),   # positive = hotter than usual
    weather_precip_sum     = ("precip",         "sum"),
    weather_precip_anomaly = ("precip_anomaly", "sum"),
    weather_drought_days   = ("drought_day",    "sum"),    # 0-7 drought days in week
).reset_index()

# ── Assign each hex to nearest grid point ─────────────────────────────────────
print("Assigning hexes to nearest grid point...")

unique_hexes = df["h3_id"].unique()

def nearest_grid(h3_id):
    lat, lon = h3.cell_to_latlng(h3_id)
    dists = [(abs(lat - glat) + abs(lon - glon), glat, glon)
             for glat, glon in grid_points]
    _, best_lat, best_lon = min(dists)
    return best_lat, best_lon

hex_to_grid = {}
for hid in tqdm(unique_hexes, desc="  Hex->grid mapping"):
    hex_to_grid[hid] = nearest_grid(hid)

df["grid_lat"] = df["h3_id"].map(lambda h: hex_to_grid[h][0])
df["grid_lon"] = df["h3_id"].map(lambda h: hex_to_grid[h][1])

# ── Merge weather into hex-week table ─────────────────────────────────────────
print("Merging weather features...")

merged = df.merge(weather_weekly, on=["grid_lat", "grid_lon", "week"], how="left")

weather_cols = ["weather_temp_max", "weather_temp_mean", "weather_temp_anomaly",
                "weather_precip_sum", "weather_precip_anomaly", "weather_drought_days"]
merged[weather_cols] = merged[weather_cols].ffill().fillna(0)

coverage = merged["weather_temp_max"].notna().mean()
print(f"  Weather coverage: {coverage:.1%} of hex-weeks have data")

# Drop intermediate grid columns
merged = merged.drop(columns=["grid_lat", "grid_lon"])

# ── Save ──────────────────────────────────────────────────────────────────────
merged.to_csv(OUT_PATH, index=False)
print(f"\nSaved {len(merged):,} rows to {OUT_PATH}")
print(f"New features: {weather_cols}")
