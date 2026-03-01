"""
One-time seed script: writes all unique H3 hexes from acled_h3.csv
into the hex_grid table in Supabase.

Run from the sentinel/ root:
    cd sentinel
    python backend/db/seed_hex_grid.py
"""

import os
import sys
import pandas as pd
import h3
from supabase import create_client
from dotenv import load_dotenv

# Load .env from backend/
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    sys.exit("SUPABASE_URL and SUPABASE_KEY must be set in backend/.env")

# ── Find the base ACLED file ──────────────────────────────────────────────────
# Walk up to sentinel root, then into data/processed/
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ACLED_PATH = os.path.join(ROOT, "data", "processed", "acled_h3.csv")

if not os.path.exists(ACLED_PATH):
    sys.exit(f"Cannot find {ACLED_PATH}. Run 01_preprocess_acled.py first.")

print(f"Loading {ACLED_PATH}...")
df = pd.read_csv(ACLED_PATH)
unique_hexes = df["h3_id"].unique()
print(f"  {len(unique_hexes):,} unique H3 hexes to seed")

# ── Build rows ────────────────────────────────────────────────────────────────
rows = []
for hid in unique_hexes:
    lat, lng = h3.cell_to_latlng(hid)
    rows.append({
        "h3_id": hid,
        "lat": round(lat, 6),
        "lng": round(lng, 6),
        # PostGIS geography point: "POINT(lng lat)"
        "centroid": f"POINT({round(lng, 6)} {round(lat, 6)})",
    })

# ── Upsert to Supabase ────────────────────────────────────────────────────────
print("Connecting to Supabase...")
client = create_client(SUPABASE_URL, SUPABASE_KEY)

BATCH = 500
print(f"Upserting {len(rows):,} rows in batches of {BATCH}...")

for i in range(0, len(rows), BATCH):
    batch = rows[i : i + BATCH]
    client.table("hex_grid").upsert(batch).execute()
    print(f"  [{i + len(batch)}/{len(rows)}] done")

print(f"\nDone. hex_grid table now has {len(rows):,} rows.")
