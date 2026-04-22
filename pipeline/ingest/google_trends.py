"""Google Trends mobilization & shelter search terms for IL, LB, SY.

Hebrew mobilization terms spike 24-72h before military operations.
Arabic shelter/war terms spike as civilians anticipate conflict.

Rate limit: pytrends throttles aggressively. Use sleep between queries.
Historical data: weekly resolution (daily only for <90 day windows).
"""
import pandas as pd
import os
import time
from pytrends.request import TrendReq

OUTPUT = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "gtrends_daily.parquet")

# Hebrew mobilization terms (Israel)
HEBREW_TERMS = {
    "צו 8": "callup_order",        # Reserve callup order
    "מילואים": "reserves",          # Military reserves
    "פיקוד העורף": "home_front",    # Home Front Command
    "מקלט": "shelter_he",           # Shelter (Hebrew)
}

# Arabic conflict terms (Lebanon, Syria)
ARABIC_TERMS = {
    "ملجأ": "shelter_ar",           # Shelter (Arabic)
    "حرب": "war_ar",               # War
    "قصف": "shelling_ar",          # Shelling/bombardment
}

# Geo codes for pytrends
GEOS = {
    "IL": "IL",
    "LB": "LB",
    "SY": "SY",
}


def fetch_trends(terms_dict, geo, timeframe="2020-01-01 2024-12-10"):
    """Fetch Google Trends data for a set of terms in a specific geography."""
    pytrends = TrendReq(hl="en-US", tz=360)
    results = {}

    for term, col_name in terms_dict.items():
        try:
            pytrends.build_payload([term], cat=0, timeframe=timeframe, geo=geo)
            df = pytrends.interest_over_time()
            if not df.empty and term in df.columns:
                results[f"gtrends_{col_name}_{geo.lower()}"] = df[term]
            time.sleep(15)  # Avoid rate limiting
        except Exception as e:
            print(f"  Warning: Failed to fetch '{term}' for {geo}: {e}")
            time.sleep(30)

    return results


def ingest_google_trends():
    if os.path.exists(OUTPUT):
        print(f"Cache hit: {OUTPUT}")
        return

    print("Fetching Google Trends data...")
    all_series = {}

    # Hebrew terms for Israel
    print("  Israel (Hebrew mobilization terms)...")
    il_data = fetch_trends(HEBREW_TERMS, "IL")
    all_series.update(il_data)

    # Arabic terms for Lebanon
    print("  Lebanon (Arabic conflict terms)...")
    lb_data = fetch_trends(ARABIC_TERMS, "LB")
    all_series.update(lb_data)

    # Arabic terms for Syria
    print("  Syria (Arabic conflict terms)...")
    sy_data = fetch_trends(ARABIC_TERMS, "SY")
    all_series.update(sy_data)

    if not all_series:
        print("  No data fetched, skipping save")
        return

    df = pd.DataFrame(all_series)
    df.index.name = "date"
    df = df.reset_index()
    df["date"] = pd.to_datetime(df["date"]).dt.date

    # Fill NaN with 0 (no search interest)
    df = df.fillna(0)

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    df.to_parquet(OUTPUT, index=False)
    print(f"  Saved {len(df)} rows, {len(df.columns)-1} features to {OUTPUT}")


if __name__ == "__main__":
    ingest_google_trends()
