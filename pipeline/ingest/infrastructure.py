import pandas as pd
import os
import requests
import h3

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

def ingest_osm(output_path="data/processed/osm_hex.parquet"):
    if os.path.exists(output_path):
        print(f"Cache hit: {output_path}")
        return

    # Need all nodes tagged amenity=hospital, amenity=school inside bounding box
    # - Send a POST request query to get hospitals and schools
    query = """
    [out:json];
    (
        node["amenity"="hospital"](32.5,34.5,34.8,37.5);
        node["amenity"="school"](32.5,34.5,34.8,37.5);
    );
    out center;
    """
    response = requests.post(OVERPASS_URL, data={"data": query}).json()

    # Need DataFrame of the known hospitals and schools
    # - Extract all locations and builds a DataFrame
    records = []
    for el in response["elements"]:
        records.append({
            "lat": el["lat"],
            "lon": el["lon"],
            "amenity": el["tags"]["amenity"]
        })
    df = pd.DataFrame(records)

    # Convert Lat/Lon point to H3 hex
    df["h3_id"] = df.apply(lambda row: h3.latlng_to_cell(row["lat"], row["lon"], 6), axis=1)

    # Need a DataFrame with per amenity per hex
    # - Split into two DataFrames, groups by hex, then merge
    hospitals = df[df["amenity"] == "hospital"].groupby("h3_id").size().reset_index(name="hospital_count")
    schools = df[df["amenity"] == "school"].groupby("h3_id").size().reset_index(name="school_count")
    agg = hospitals.merge(schools, on="h3_id", how="outer").fillna(0)

    # Save file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    agg.to_parquet(output_path, index=False)
    print(f"Saved {len(agg)} rows to {output_path}")  

    
if __name__ == "__main__":
    ingest_osm()
