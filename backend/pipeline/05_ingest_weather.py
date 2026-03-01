"""
Step 5: Weather Features via Open-Meteo (free, no API key)

Downloads daily temperature and precipitation for a 0.5-degree grid covering
the Levant bounding box, assigns each H3 hex to its nearest grid point,
and merges heat/precip anomaly features into the training table.

Features added:
  temp_max          - daily maximum temperature (°C)
  temp_anomaly_30d  - temp_max minus 30-day rolling mean per grid point (heat spike)
  precip_mm         - daily precipitation sum (mm)
  precip_spike      - 1 if precip > 90th-pct for that calendar month at that location

Output: data/processed/acled_h3_gdelt_firms_weather.csv
"""

import pandas as pd
import numpy as np
import requests
import h3
import time
import os
from tqdm import tqdm

# ── Config ────────────────────────────────────────────────────────────────────
IN_PATH   = "data/processed/acled_h3_gdelt_firms.csv"
OUT_PATH  = "data/processed/acled_h3_gdelt_firms_weather.csv"
CACHE_DIR = "data/raw/weather_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# Levant bounding box
LAT_MIN, LAT_MAX = 29.5, 37.5
LON_MIN, LON_MAX = 33.5, 42.5
GRID_STEP = 0.5   # degrees

START_DATE = "2020-01-01"
END_DATE   = "2024-12-10"

OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"

# ── Generate 0.5° grid ────────────────────────────────────────────────────────
lats = np.round(np.arange(LAT_MIN, LAT_MAX + GRID_STEP, GRID_STEP), 2)
lons = np.round(np.arange(LON_MIN, LON_MAX + GRID_STEP, GRID_STEP), 2)
grid_points = [(la, lo) for la in lats for lo in lons]
print(f"Weather grid: {len(grid_points)} points at {GRID_STEP}° resolution")

# ── Download weather per grid point (with caching) ────────────────────────────
def fetch_weather(lat, lon):
    cache_file = os.path.join(CACHE_DIR, f"{lat}_{lon}.csv")
    if os.path.exists(cache_file):
        return pd.read_csv(cache_file, parse_dates=["date"])
    params = {
        "latitude":   lat,
        "longitude":  lon,
        "start_date": START_DATE,
        "end_date":   END_DATE,
        "daily":      "temperature_2m_max,temperature_2m_mean,precipitation_sum",
        "timezone":   "GMT",
    }
    for attempt in range(5):
        try:
            r = requests.get(OPEN_METEO_URL, params=params, timeout=30)
            r.raise_for_status()
            data = r.json().get("daily", {})
            if not data:
                return None
            df_w = pd.DataFrame({
                "date":      pd.to_datetime(data["time"]),
                "temp_max":  data["temperature_2m_max"],
                "temp_mean": data["temperature_2m_mean"],
                "precip_mm": data["precipitation_sum"],
            })
            df_w["grid_lat"] = lat
            df_w["grid_lon"] = lon
            df_w.to_csv(cache_file, index=False)
            return df_w
        except Exception as e:
            if attempt == 4:
                print(f"  ✗ failed ({lat},{lon}): {e}")
                return None
            time.sleep(2 ** attempt)

print("Downloading weather data (cached after first run)...")
all_weather = []
for lat, lon in tqdm(grid_points):
    df_w = fetch_weather(lat, lon)
    if df_w is not None:
        all_weather.append(df_w)
    time.sleep(0.06)   # polite rate limiting

weather = pd.concat(all_weather, ignore_index=True)
print(f"  Downloaded: {len(weather):,} daily grid-point records")

# ── Compute anomalies ─────────────────────────────────────────────────────────
print("Computing anomalies...")
weather = weather.sort_values(["grid_lat", "grid_lon", "date"])

# 30-day rolling mean temperature anomaly (heat spike signal)
weather["temp_roll30"] = (
    weather.groupby(["grid_lat", "grid_lon"])["temp_max"]
    .transform(lambda x: x.rolling(30, min_periods=7).mean())
)
weather["temp_anomaly_30d"] = (weather["temp_max"] - weather["temp_roll30"]).fillna(0)

# Precip spike: > 90th percentile for that calendar month at that location
weather["month"] = weather["date"].dt.month
p90 = (
    weather.groupby(["grid_lat", "grid_lon", "month"])["precip_mm"]
    .transform(lambda x: x.quantile(0.90))
)
weather["precip_spike_w"] = (weather["precip_mm"] > p90).astype(int)
weather = weather.drop(columns=["temp_roll30", "month"])
weather = weather.rename(columns={"precip_spike_w": "precip_spike"})

# ── Load training table ────────────────────────────────────────────────────────
print(f"\nLoading {IN_PATH}...")
df = pd.read_csv(IN_PATH, parse_dates=["event_date"], low_memory=False)
print(f"  {len(df):,} rows  |  {df['h3_id'].nunique():,} hexes")

# ── Map each hex to nearest grid point ────────────────────────────────────────
print("Mapping hexes to nearest weather grid point...")
unique_hexes = df["h3_id"].unique()
grid_arr = np.array(grid_points)

hex_grid_rows = []
for hx in unique_hexes:
    hlat, hlon = h3.cell_to_latlng(hx)
    dists = (grid_arr[:, 0] - hlat) ** 2 + (grid_arr[:, 1] - hlon) ** 2
    best  = grid_points[int(np.argmin(dists))]
    hex_grid_rows.append({"h3_id": hx, "grid_lat": best[0], "grid_lon": best[1]})

hex_grid_df = pd.DataFrame(hex_grid_rows)

# ── Merge ──────────────────────────────────────────────────────────────────────
print("Merging weather features...")
weather_slim = weather[["grid_lat", "grid_lon", "date",
                         "temp_max", "temp_anomaly_30d",
                         "precip_mm", "precip_spike"]].rename(columns={"date": "event_date"})

df = df.merge(hex_grid_df, on="h3_id", how="left")
df = df.merge(weather_slim, on=["grid_lat", "grid_lon", "event_date"], how="left")
df = df.drop(columns=["grid_lat", "grid_lon"])

fill_rate = (df["temp_max"].notna() & (df["temp_max"] != 0)).mean()
for col in ["temp_max", "temp_anomaly_30d", "precip_mm", "precip_spike"]:
    df[col] = df[col].fillna(0)

print(f"  Weather fill rate: {fill_rate*100:.1f}%")

# ── Save ──────────────────────────────────────────────────────────────────────
df.to_csv(OUT_PATH, index=False)
print(f"\nSaved {len(df):,} rows to {OUT_PATH}")
print("New features: temp_max, temp_anomaly_30d, precip_mm, precip_spike")
