import pandas as pd
import requests
import os
import h3
from dotenv import load_dotenv

load_dotenv()

WFP_API_URL = "https://api.vam.wfp.org/economicExplorer/CountryDate"
COUNTRIES = [{"id": 115, "name": "Lebanon"}, {"id": 238, "name": "Syria"}, {"id": 107, "name": "Israel"}]

def ingest_wfp(output_path="data/processed/wfp_hex_daily.parquet"):
    if os.path.exists(output_path):
        print(f"Cache hit: {output_path}")
        return
    
    # Need each country's food market statistics
    # - Request nested JSON, reformat each item into a row
    all_rows = []
    for country in COUNTRIES:
        response = requests.get(WFP_API_URL, params={"CountryId": country["id"]}).json()
        for item in response:
            all_rows.append({
                "lat": item["lat"],
                "lon": item["lon"],
                "date": item["date"],
                "price": item["price"],
                "category": item["category"]
            })


    # Need to filter DataFrame
    # - Filter out NA values, Bound by lat/lon, Assign H3 IDs, Parse Dates
    df = pd.DataFrame(all_rows)
    df = df.dropna(subset=["lat", "lon"])
    df = df[(df["lat"] >= 32.5) & (df['lat'] <= 34.8) & (df["lon"] >= 34.5) & (df["lon"] <= 37.5)]
    df["h3_id"] = df.apply(lambda row: h3.latlng_to_cell(row["lat"], row["lon"], 6), axis=1)
    df["date"] = pd.to_datetime(df["date"]).dt.date

    # Need to add food price statistics
    # - Group by Hex ID and date, then aggregate overall food prices and bread prices
    agg = df.groupby(["h3_id", "date"]).agg(
        price_mean=("price", "mean"),
    ).reset_index()
    bread = df[df["category"] == "Bread"].groupby(["h3_id", "date"]).agg(
        price_bread = ("price", "mean"),
    ).reset_index()
    agg = agg.merge(bread, on=["h3_id", "date"], how="left")


    # Save file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    agg.to_parquet(output_path, index=False)
    print(f"Saved {len(agg)} rows to {output_path}")  

    
if __name__ == "__main__":
    ingest_wfp()
