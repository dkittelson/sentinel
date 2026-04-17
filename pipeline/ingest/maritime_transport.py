import pandas as pd
import os
import requests

PORTWATCH_URL = "https://services9.arcgis.com/weJ1QsnbMYJlCHdG/ArcGIS/rest/services/Daily_Ports_Data/FeatureServer/0/query"

PORTS = {
    "Beirut": "port132",
    "Tripoli_LB": "port1274",
    "Haifa": "port435",
    "Ashdod": "port73",
}

def ingest_portwatch(output_path="data/processed/portwatch_daily.parquet"):
    if os.path.exists(output_path):
        print(f"Cache hit: {output_path}")
        return
    
    # Need daily vessel counts from 2020-2025 
    # - For each port, request daily counts from API, flatten into records list, build DataFrame
    records = []
    for port_name, port_code in PORTS.items():
        response = requests.get(PORTWATCH_URL, params={
            "where": f"portid='{port_code}' AND date>='2020-01-01' AND date<='2025-12-31'",
            "outFields": "date,portid,portname,portcalls",
            "orderByFields": "date ASC",
            "f": "json",
            "resultRecordCount": 2000
        })
        for feature in response.json()["features"]:
            a = feature["attributes"]
            records.append({
                "port": port_name,
                "date": a["date"],
                "portcalls": a["portcalls"]
            })
    df = pd.DataFrame(records)

    # Parse dates
    df["date"] = pd.to_datetime(df["date"]).dt.date

    # Save file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_parquet(output_path, index=False)
    print(f"Saved {len(df)} rows to {output_path}")  
        


if __name__ == "__main__": ingest_portwatch()