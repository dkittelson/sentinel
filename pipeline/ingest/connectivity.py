import pandas as pd
import requests
import os
import h3
from dotenv import load_dotenv

load_dotenv()

IODA_BASE_URL = "https://api.ioda.caida.org/v2/signals/raw/country/"
COUNTRIES = ["IL", "LB", "SY"]

def ingest_ioda(output_path="data/processed/ioda_daily.parquet"):
    if os.path.exists(output_path):
        print(f"Cache hit: {output_path}")
        return

    # Need to JSON file for each country
    # - Build the start and end date and query the IODA API to get each country's JSON
    # - Flatten IODA's nested JSON into flat list of rows
    start = int(pd.Timestamp("2020-01-01").timestamp())
    end = int(pd.Timestamp("2025-12-31").timestamp())
    all_rows = []
    for country in COUNTRIES:
        url = IODA_BASE_URL + country + f"?from={start}&until={end}"
        response = requests.get(url).json()
        for datasource in response["data"]:
            for timestamp, score in datasource["values"]:
                all_rows.append({
                    "country": country,
                    "date": pd.Timestamp(timestamp, unit="s").date(),
                    "score": score
                })

    # Need a DataFrame 
    # - Build DataFrame, group by country and date, average scores, convert country rows to columns
    df = pd.DataFrame(all_rows)
    df = df.groupby(["country", "date"])["score"].mean().reset_index()
    df = df.pivot(index="date", columns="country", values="score").reset_index()
    df.columns = ["date", "ioda_il", "ioda_lb", "ioda_sy"]

    # Save file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_parquet(output_path, index=False)
    print(f"Saved {len(df)} rows to {output_path}")  

    
if __name__ == "__main__":
    ingest_ioda()





    
