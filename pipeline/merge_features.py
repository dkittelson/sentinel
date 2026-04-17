import pandas as pd
import os

def merge_features(output_path="data/processed/sentinel_v2_features.parquet"):
    if os.path.exists(output_path):
        print(f"Cache hit: {output_path}")
        return
    
    # Load all parquets
    BASE = "data/processed"
    SOURCES = {
        "conflict":    f"{BASE}/ucdp_hex_daily.parquet",
        "nightlights": f"{BASE}/nightlights_hex_daily.parquet",
        "gdelt":       f"{BASE}/gdelt_hex_daily.parquet",
        "pikud":       f"{BASE}/pikud_hex_daily.parquet",
        "portwatch":   f"{BASE}/portwatch_daily.parquet",
        "calendar":    f"{BASE}/calendar_daily.parquet",
        "worldpop":    f"{BASE}/worldpop_hex.parquet",
        "osm":         f"{BASE}/osm_hex.parquet",
        "ofac":        f"{BASE}/ofac_weekly.parquet",
    }

    # Build master hex-date grid --> one row = one hex on one day with every feature as a column
    conflict = pd.read_parquet(SOURCES["conflict"])
    hex_ids = conflict["h3_id"].unique()
    dates = pd.date_range("2020-01-01", "2025-12-31").date
    master = pd.DataFrame(
        pd.MultiIndex.from_product([hex_ids, dates], names=["h3_id", "date"]).tolist(),
        columns=["h3_id", "date"]
    )   

    # Join time-series sources
    for name in ["conflict", "nightlights", "gdelt", "pikud"]:
        df = pd.read_parquet(SOURCES[name])
        master = master.merge(df, on=["h3_id", "date"], how="left")

    # Join static sources
    for name in ["worldpop", "osm"]:
        df = pd.read_parquet(SOURCES[name])
        master = master.merge(df, on="h3_id", how="left")

    # Join date-only sources
    calendar = pd.read_parquet(SOURCES["calendar"])
    master = master.merge(calendar, on="date", how="left")

    # Fill NaN values and convert boolean to ints
    master = master.fillna(0)
    master["ever_had_event_5yr"] = master["ever_had_event_5yr"].astype(int)

    # Save file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    master.to_parquet(output_path, index=False)
    print(f"Saved {len(master)} rows to {output_path}")   

if __name__ == "__main__":
    merge_features()