import pandas as pd
import requests
import zipfile
import h3
import os

RAW_PATH = "data/raw/GEDEvent_v25_1.csv"
ZIP_URL = "https://ucdp.uu.se/downloads/ged/ged251-csv.zip"

def ingest_ucdp(output_path="data/processed/ucdp_hex_daily.parquet"):
    """Downloads UCDP-GED, filters to Lat/Lon, snaps every event to an H3 hex, collapses it to one row per hex per day --> GROUND TRUTH"""

    # --- Download & Extract Zip ---
    if not os.path.exists(RAW_PATH):

        # download bytes
        raw_bytes = requests.get(ZIP_URL).content

        # write to data/raw/ucdp.zip
        with open("data/raw/ucdp.zip", "wb") as f:
            f.write(raw_bytes)

        # extract zip file
        with zipfile.ZipFile("data/raw/ucdp.zip") as zip:
            print(zip.namelist())
            zip.extract(zip.namelist()[0], "data/raw/")

    # --- Load & Filter ---
    df = pd.read_csv(RAW_PATH, low_memory=False)
    df = df.dropna(subset=["latitude", "longitude"])
    df = df[(df["latitude"] >= 32.5) & (df['latitude'] <= 34.8) & (df["longitude"] >= 34.5) & (df["longitude"] <= 37.5)]

    # --- Parse Dates ---
    df["date"] = pd.to_datetime(df["date_start"]).dt.date 

    # --- Assign H3 ---
    df["h3_id"] = df.apply(lambda row: h3.latlng_to_cell(row["latitude"], row["longitude"], 6), axis=1)

    # --- Convert to Per Hex Day ---
    df["is_state_based"] = (df["type_of_violence"] == 1)
    df["is_non_state"] = (df["type_of_violence"] == 2)
    df["is_one_sided"] = (df["type_of_violence"] == 3)

    agg = df.groupby(["h3_id", "date"]).agg(
        event_count=("best", "size"),
        fatality_best=("best", "sum"),
        is_state_based=("is_state_based", "sum"),
        is_non_state=("is_non_state", "sum"),
        is_one_sided=("is_one_sided", "sum"),
    ).reset_index()

    # --- Save DataFrame as a Parquet ---
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    agg.to_parquet(output_path, index=False)
    print(f"Saved {len(agg)} rows to {output_path}")

def compute_rolling_features(output_path="data/processed/ucdp_hex_daily.parquet"):
    """Adds 2 columns: How many conflict events happened in this hex in past 14 days (dangerous_roll_14d) and has the hex ever seen conflict in past 5 years (ever_had_event_5yr)"""

    # --- Load Parquet ---
    df = pd.read_parquet(output_path)

    # --- Sort by Hex & Date ---
    df = df.sort_values(["h3_id", "date"])

    # --- Add 14 Day Rolling Features Column (Continuation Data) ---
    df["dangerous_roll14d"] = df.groupby("h3_id")["event_count"].rolling(14).sum().reset_index(level=0, drop=True)
    df["dangerous_roll14d"] = df["dangerous_roll14d"].fillna(0)

    # --- Add Had Event In Past 1 Year Column (Onset Data) ---
    df["ever_had_event_5yr"] = (df.groupby("h3_id")["event_count"].rolling(365).sum().reset_index(level=0, drop=True) > 0)
    df["ever_had_event_5yr"] = df["ever_had_event_5yr"].fillna(False)

    df.to_parquet(output_path, index=False)

    print(f"Rolling features added, {len(df)} rows")

if __name__ == "__main__":
    ingest_ucdp()
    compute_rolling_features()
    



        




