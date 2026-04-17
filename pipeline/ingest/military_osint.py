import pandas as pd
import requests
import os
import io
import h3
from dotenv import load_dotenv
import json

load_dotenv()

PIKUD_LIVE_URL = "https://www.oref.org.il/warningMessages/alert/History/AlertsHistory.json"
PIKUD_HISTORICAL_URL = "https://raw.githubusercontent.com/oref-alerts/oref-alerts.github.io/main/events.js"

CITY_COORDS = {
    "תל אביב": (32.0853, 34.7818),
    "חיפה": (32.7940, 34.9896),
    "נהריה": (33.0048, 35.0950),
    "קריית שמונה": (33.2072, 35.5702),
    "צפת": (32.9646, 35.4960),
    "טבריה": (32.7922, 35.5312),
    "עכו": (32.9233, 35.0694),
    "נצרת": (32.6996, 35.3035),
}



def ingest_pikud_historical(output_path="data/processed/pikud_hex_daily.parquet"):
    if os.path.exists(output_path):
        print(f"Cache hit: {output_path}")
        return
    
    # Need to get pikud DataFrame of each year
    # - Download JS file, strip JS wrapper, parse JSON, flatten into rows
    response = requests.get(PIKUD_HISTORICAL_URL)
    text = response.text
    start = text.index("const EVENTS_BY_AREA = ") + len("const EVENTS_BY_AREA = ")
    end = text.rindex(";")
    events_by_area = json.loads(text[start:end])

    all_rows = []
    for area_code, area_data in events_by_area.items():
        city = area_data["name"]
        for event in area_data["events"]:
            all_rows.append({
                "alertDate": event["d"],
                "city": city,
            })
    df = pd.DataFrame(all_rows)

    # Need to map city's to coordinates so they can be assigned a hex
    df["lat"] = df["city"].map(lambda c: CITY_COORDS.get(c, (None, None))[0])
    df["lon"] = df["city"].map(lambda c: CITY_COORDS.get(c, (None, None))[1])
    df = df.dropna(subset=["lat", "lon"])

    # Need a DataFrame with one row per hex per day
    # - Parse Dates, Assign H3 IDs, Group all siren counts for specific days
    df["date"] = pd.to_datetime(df["alertDate"]).dt.date
    df["h3_id"] = [h3.latlng_to_cell(lat, lon, 6) for lat, lon in zip(df["lat"], df["lon"])]
    agg = df.groupby(["h3_id", "date"]).agg(
        siren_count=("alertDate", "size"),
    ).reset_index()

    # Save file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    agg.to_parquet(output_path, index=False)
    print(f"Saved {len(agg)} rows to {output_path}")  

def ingest_pikud_live(output_path="data/processed/pikud_hex_daily.parquet"):
    
    # Need to get a DataFrame with one row per city per alert
    # - Parse cities and build alerts for each city, build DataFrame
    raw = requests.get(PIKUD_LIVE_URL, headers={"Referer": "https://www.oref.org.il/"})
    if not raw.text.strip() or "<HTML>" in raw.text:
        print("Live endpoint blocked or no alerts")
        return
    response = raw.json()
    all_rows = []
    for alert in response:
        for city in alert["data"]:
            all_rows.append({
                "alertDate": alert["alertDate"],
                "city": city,
                "title": alert["title"]
            })
    df = pd.DataFrame(all_rows)

    # Need to map city's to coordinates so they can be assigned a hex
    df["lat"] = df["city"].map(lambda c: CITY_COORDS.get(c, (None, None))[0])
    df["lon"] = df["city"].map(lambda c: CITY_COORDS.get(c, (None, None))[1])
    df = df.dropna(subset=["lat", "lon"])

    # Need a DataFrame with one row per hex per day
    # - Parse Dates, Assign H3 IDs, Group all siren counts for specific days
    df["date"] = pd.to_datetime(df["alertDate"]).dt.date
    df["h3_id"] = [h3.latlng_to_cell(lat, lon, 6) for lat, lon in zip(df["lat"], df["lon"])]
    agg = df.groupby(["h3_id", "date"]).agg(
        siren_count=("alertDate", "size"),
    ).reset_index()

    # If file exists, append
    if os.path.exists(output_path):
        existing = pd.read_parquet(output_path)
        agg = pd.concat([existing, agg], ignore_index=True).drop_duplicates()

    # Save file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    agg.to_parquet(output_path, index=False)
    print(f"Saved {len(agg)} rows to {output_path}")  



if __name__ == "__main__":
    ingest_pikud_historical()
    ingest_pikud_live()