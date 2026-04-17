import pandas as pd
import os 
import requests
import xml.etree.ElementTree as ET

OFAC_URL = "https://www.treasury.gov/ofac/downloads/sdn.xml"
TARGET_COUNTRIES = ["LB", "SY", "IR"]

def ingest_ofac(output_path="data/processed/ofac_weekly.parquet"):
    if os.path.exists(output_path):
        print(f"Cache hit: {output_path}")
        return
    
    # Download and parse XML
    response = requests.get(OFAC_URL)
    root = ET.fromstring(response.content)
    
    # Need the OFAC sanctions list
    # - Loop through every sanctioned entity, records program name and data if under Lebanon, Syria, Iran
    ns = "{https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/XML}"
    records = []
    for entry in root.findall(f"{ns}sdnEntry"):
        program_el = entry.find(f"{ns}programList/{ns}program")
        if program_el is not None and any(c in program_el.text.upper() for c in ["SYRIA", "LEBANON", "IRAN"]):
            records.append({"country": program_el.text, "date": pd.Timestamp.today().date()})
    df = pd.DataFrame(records).groupby(["country", "date"]).size().reset_index(name="total_designations")

    # Save file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_parquet(output_path, index=False)
    print(f"Saved {len(df)} rows to {output_path}")  

    
if __name__ == "__main__":
    ingest_ofac()

