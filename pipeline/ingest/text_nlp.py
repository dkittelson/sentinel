import pandas as pd
import numpy as np   
import requests
import zipfile
import os
import h3
from geopy.distance import geodesic
from dotenv import load_dotenv

GDELT_BASE_URL = "http://data.gdeltproject.org/gdeltv2/"
GDELT_COLS  = [0, 1, 30, 31, 34, 56, 57]
GDELT_NAMES = ["event_id", "day", "goldstein", "mentions", "tone", "lat", "lon"]

load_dotenv()

def ingest_gdelt(output_path="data/processed/gdelt_hex_daily.parquet"):
    if os.path.exists(output_path):
        print(f"Cache hit: {output_path}")
        return
    
    # Need collection of all events per day
    # - Loop through each day and build a stack of DataFrame's of events per day
    all_dfs = []
    date_range = pd.date_range("2020-01-01", "2025-12-31")
    for date in date_range: 
        filename = date.strftime("%Y%m%d") + "000000.export.CSV.zip"
        raw_bytes = requests.get(GDELT_BASE_URL + filename).content
        with open("data/raw/gdelt.zip", "wb") as f:
            f.write(raw_bytes)
        with zipfile.ZipFile("data/raw/gdelt.zip") as zf:
            print(zf.namelist())
            zf.extract(zf.namelist()[0], "data/raw/")
            csv_path = "data/raw/" + zf.namelist()[0]
        df = pd.read_csv(csv_path, sep="\t", header=None, usecols=GDELT_COLS)
        df.columns = GDELT_NAMES
        all_dfs.append(df)
    df = pd.concat(all_dfs, ignore_index=True) # stack all dfs

    # Need to filter the stacked DataFrames
    # - Drop Rows with NA Values and fix events to Levant
    df = df.dropna(subset=["lat", "lon"])
    print(df[["lat", "lon"]].describe())
    df = df[(df["lat"] >= 32.5) & (df['lat'] <= 34.8) & (df["lon"] >= 34.5) & (df["lon"] <= 37.5)]
    df["h3_id"] = [h3.latlng_to_cell(lat, lon, 6) for lat, lon in zip(df["lat"], df["lon"])]

    # Need to group the stacked DataFrames in order to get Per Hex Per Day 
    # - Group rows by Hex ID and Date, compute event count, goldstein mean, tone mean, mentions sum
    df["date"] = pd.to_datetime(df["day"], format="%Y%m%d").dt.date
    agg = df.groupby(["h3_id", "date"]).agg(
        event_count=("event_id", "size"),
        goldstein_mean=("goldstein", "mean"),
        tone_mean=("tone", "mean"),
        mentions_sum=("mentions", "sum"),
    ).reset_index()

    # Save file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    agg.to_parquet(output_path, index=False)
    print(f"Saved {len(agg)} rows to {output_path}")   

if __name__ == "__main__":
    ingest_gdelt()







