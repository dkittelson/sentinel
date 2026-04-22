"""GDELT events + GKG expanded ingest for the Levant.

Two GDELT data streams:

  Stream 1 — Events 2.0 export (CAMEO-coded event records):
    QuadClass (verbal/material cooperation/conflict), EventRootCode, GoldsteinScale,
    NumMentions, NumSources, NumArticles, AvgTone, actor country codes.
    Downloaded as YYYYMMDD000000.export.CSV.zip (~1-5 MB/day compressed).

  Stream 2 — GKG 2.1 daily sample (disable with --skip-gkg):
    The midnight UTC 15-min GKG file (~30-80 MB/day compressed).
    Filtered to articles with ≥1 V2Location in Israel (IS), Lebanon (LE), or Syria (SY).
    URL-deduplicated before aggregation to hex (avoids double-counting syndicated content).
    Extracts: GCAM emotional dimensions (NRC Fear c12.3, LIWC Anger c2.1, LIWC Anxiety c2.15),
    CRISISLEX crisis theme count, Arabic-language article count via TranslationInfo.

Output: pipeline/data/processed/gdelt_hex_daily.parquet
Columns:
  h3_id                  — H3 resolution-6 hex ID
  date                   — date
  gdelt_event_count      — events in hex that day
  gdelt_avg_tone         — mean article tone (negative = hostile)
  gdelt_min_goldstein    — most-destabilizing event Goldstein score (lower = worse)
  gdelt_avg_goldstein    — mean Goldstein scale
  gdelt_num_articles     — total article mentions across events
  gdelt_num_sources      — mean NumSources per event (media source breadth)
  gdelt_hostility        — fraction of events in material conflict (QuadClass 4)
  gdelt_verbal_conflict  — fraction of events in verbal conflict (QuadClass 3)
  gdelt_coop_fraction    — fraction of events in verbal/material cooperation (QuadClass 1-2)
  gdelt_cameo_conflict   — fraction of events in any conflict quadrant (3 or 4)
  gdelt_protest_count    — CAMEO root-14 events (protest/demonstrate)
  gdelt_threaten_count   — CAMEO root-13 events (threaten)
  gdelt_assault_count    — CAMEO root-18 events (physically assault)
  gdelt_fight_count      — CAMEO root-19 events (fight/armed attack)
  gdelt_fear_score       — mean NRC Fear score (GCAM c12.3; 0 if --skip-gkg)
  gdelt_anger_score      — mean LIWC Anger score (GCAM c2.1; 0 if --skip-gkg)
  gdelt_anxiety_score    — mean LIWC Anxiety score (GCAM c2.15; 0 if --skip-gkg)
  gdelt_crisislex_count  — CRISISLEX theme mentions per hex-day (0 if --skip-gkg)
  gdelt_arabic_count     — Arabic-source article count (0 if --skip-gkg)

Usage:
  python pipeline/ingest/text_nlp.py                    # yesterday
  python pipeline/ingest/text_nlp.py --backfill         # 2020-01-01 to yesterday
  python pipeline/ingest/text_nlp.py --date 2024-06-01  # specific date
  python pipeline/ingest/text_nlp.py --skip-gkg         # events only (faster)
"""

import argparse
import io
import os
import sys
import zipfile
from datetime import datetime, timedelta

import h3
import numpy as np
import pandas as pd
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ml.config import H3_RESOLUTION

OUTPUT   = os.path.join(os.path.dirname(__file__), "..", "data", "processed",
                         "gdelt_hex_daily.parquet")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
BASE_URL = "http://data.gdeltproject.org/gdeltv2/"

# ── Levant spatial filter ─────────────────────────────────────────────────────
# GDELT GKG uses FIPS 10-4 country codes for V2Locations
LEVANT_FIPS = {"IS", "LE", "SY"}
LAT_MIN, LAT_MAX = 29.0, 35.5
LON_MIN, LON_MAX = 33.5, 38.5

# ── Events 2.0 column schema ──────────────────────────────────────────────────
# Columns selected from the 61-column tab-separated export
EVT_COLS = [0, 1, 7, 17, 26, 28, 29, 30, 31, 32, 33, 34, 56, 57, 60]
EVT_NAMES = [
    "event_id", "day",
    "actor1_cc", "actor2_cc",
    "cameo_code", "cameo_root",
    "quad_class", "goldstein", "num_mentions", "num_sources", "num_articles",
    "avg_tone",
    "lat", "lon", "url",
]

# ── GKG 2.1 column schema ─────────────────────────────────────────────────────
# Columns selected from the 27-column tab-separated GKG file
GKG_COLS  = [1, 4, 8, 10, 17, 25]
GKG_NAMES = ["date_raw", "url", "v2themes", "v2locations", "v2gcam", "trans_info"]

# GDELT GCAM dimension codes → our output column names
# c2.1:  LIWC 2007 Anger
# c2.15: LIWC 2007 Anxiety (worried/nervous/scared)
# c12.3: NRC Word-Emotion Lexicon Fear
GCAM_DIMS = {
    "c2.1":  "gdelt_anger_score",
    "c2.15": "gdelt_anxiety_score",
    "c12.3": "gdelt_fear_score",
}


# ── Download helpers ──────────────────────────────────────────────────────────

def _gdelt_url(date_str: str, kind: str) -> str:
    """Build GDELT midnight-UTC file URL. kind: 'events' or 'gkg'."""
    ts = date_str.replace("-", "") + "000000"
    ext = "export.CSV.zip" if kind == "events" else "gkg.csv.zip"
    return f"{BASE_URL}{ts}.{ext}"


def _fetch_zip(url: str, timeout: int = 120) -> bytes | None:
    try:
        resp = requests.get(url, timeout=timeout, stream=True)
        if resp.status_code == 200:
            return resp.content
        print(f"    HTTP {resp.status_code}: {url}")
    except Exception as exc:
        print(f"    Download error: {exc}")
    return None


def _parse_zip_csv(raw: bytes, cols: list[int], names: list[str]) -> pd.DataFrame | None:
    """Read selected columns from the first CSV inside a zip archive."""
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            with zf.open(zf.namelist()[0]) as f:
                df = pd.read_csv(
                    f, sep="\t", header=None, usecols=cols,
                    low_memory=False, on_bad_lines="skip",
                    encoding_errors="replace",
                )
        df.columns = names
        return df
    except Exception as exc:
        print(f"    Parse error: {exc}")
    return None


# ── Events stream ─────────────────────────────────────────────────────────────

def _fetch_events(date_str: str) -> pd.DataFrame:
    """Download one day's GDELT events, filtered to the Levant bbox."""
    raw = _fetch_zip(_gdelt_url(date_str, "events"))
    if raw is None:
        return pd.DataFrame(columns=EVT_NAMES)

    df = _parse_zip_csv(raw, EVT_COLS, EVT_NAMES)
    if df is None or df.empty:
        return pd.DataFrame(columns=EVT_NAMES)

    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df = df.dropna(subset=["lat", "lon"])
    df = df[
        (df["lat"] >= LAT_MIN) & (df["lat"] <= LAT_MAX) &
        (df["lon"] >= LON_MIN) & (df["lon"] <= LON_MAX)
    ]
    return df


def _aggregate_events(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate Levant events to hex-level features."""
    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    df["h3_id"] = [h3.latlng_to_cell(lat, lon, H3_RESOLUTION)
                   for lat, lon in zip(df["lat"], df["lon"])]

    df["quad_class"] = pd.to_numeric(df["quad_class"], errors="coerce").fillna(0)
    df["cameo_root"]  = df["cameo_root"].astype(str).str.strip()
    df["goldstein"]   = pd.to_numeric(df["goldstein"], errors="coerce")
    df["avg_tone"]    = pd.to_numeric(df["avg_tone"], errors="coerce")
    df["num_sources"] = pd.to_numeric(df["num_sources"], errors="coerce")
    df["num_articles"]= pd.to_numeric(df["num_articles"], errors="coerce")

    agg = df.groupby("h3_id").agg(
        gdelt_event_count  = ("event_id", "count"),
        gdelt_avg_tone     = ("avg_tone",     "mean"),
        gdelt_min_goldstein= ("goldstein",    "min"),
        gdelt_avg_goldstein= ("goldstein",    "mean"),
        gdelt_num_articles = ("num_articles", "sum"),
        gdelt_num_sources  = ("num_sources",  "mean"),
    ).reset_index()

    total = agg["gdelt_event_count"].clip(lower=1)

    for qc, col in [(4, "_mat4"), (3, "_verb3")]:
        counts = df[df["quad_class"] == qc].groupby("h3_id").size().rename(col)
        agg = agg.merge(counts.reset_index(), on="h3_id", how="left")

    coop_counts = (df[df["quad_class"].isin([1.0, 2.0])]
                   .groupby("h3_id").size().rename("_coop"))
    agg = agg.merge(coop_counts.reset_index(), on="h3_id", how="left")
    agg[["_mat4", "_verb3", "_coop"]] = agg[["_mat4", "_verb3", "_coop"]].fillna(0)

    agg["gdelt_hostility"]       = agg["_mat4"]                    / total
    agg["gdelt_verbal_conflict"] = agg["_verb3"]                   / total
    agg["gdelt_coop_fraction"]   = agg["_coop"]                    / total
    agg["gdelt_cameo_conflict"]  = (agg["_mat4"] + agg["_verb3"]) / total
    agg = agg.drop(columns=["_mat4", "_verb3", "_coop"])

    for code, col in [
        ("14", "gdelt_protest_count"),
        ("13", "gdelt_threaten_count"),
        ("18", "gdelt_assault_count"),
        ("19", "gdelt_fight_count"),
    ]:
        counts = df[df["cameo_root"] == code].groupby("h3_id").size().rename(col)
        agg = agg.merge(counts.reset_index(), on="h3_id", how="left")
        agg[col] = agg[col].fillna(0).astype(int)

    return agg


# ── GKG stream ────────────────────────────────────────────────────────────────

def _levant_latlon(v2locs: str) -> tuple[float, float] | None:
    """Return (lat, lon) of the first Levant V2Location entry, or None.

    V2Locations format: FullName#CountryCode#ADM1#ADM2#ADM3#Lat#Long#FeatureID#Offset;...
    GDELT uses FIPS 10-4 country codes: IS=Israel, LE=Lebanon, SY=Syria.
    """
    if not isinstance(v2locs, str) or not v2locs:
        return None
    for entry in v2locs.split(";"):
        parts = entry.split("#")
        if len(parts) >= 7 and parts[1] in LEVANT_FIPS:
            try:
                return float(parts[5]), float(parts[6])
            except (ValueError, IndexError):
                continue
    return None


def _parse_gcam(gcam_str: str) -> dict:
    """Extract GCAM emotional dimensions from a V2GCAM string.

    V2GCAM format: 'wc:TOTAL,c2.1:N,c2.15:N,c12.3:N,...'
    Returns a dict mapping GCAM_DIMS output column names to float values.
    """
    result = {}
    if not isinstance(gcam_str, str) or not gcam_str:
        return result
    for item in gcam_str.split(","):
        key, _, val = item.partition(":")
        if key in GCAM_DIMS:
            try:
                result[GCAM_DIMS[key]] = float(val)
            except ValueError:
                pass
    return result


def _crisislex_count(v2themes: str) -> int:
    """Count CRISISLEX theme mentions in V2Themes.

    V2Themes format: 'THEME,offset;THEME,offset;...'
    CRISISLEX themes prefix 'CRISISLEX_' cover 8 crisis types.
    """
    if not isinstance(v2themes, str) or not v2themes:
        return 0
    return sum(1 for t in v2themes.split(";")
               if t.split(",")[0].startswith("CRISISLEX"))


def _is_arabic(trans_info: str) -> bool:
    """Detect Arabic-language source from TranslationInfo field.

    TranslationInfo format: 'srclc:XX;...' where XX is ISO 639-1 language code.
    'srclc:ar' means the original article was in Arabic before translation.
    """
    return isinstance(trans_info, str) and "srclc:ar" in trans_info


def _fetch_gkg(date_str: str) -> pd.DataFrame:
    """Download and parse the midnight UTC GKG 15-min file for one day."""
    url = _gdelt_url(date_str, "gkg")
    print(f"    GKG sample: {url.split('/')[-1]}")
    raw = _fetch_zip(url, timeout=300)
    if raw is None:
        return pd.DataFrame(columns=GKG_NAMES)

    df = _parse_zip_csv(raw, GKG_COLS, GKG_NAMES)
    if df is None or df.empty:
        return pd.DataFrame(columns=GKG_NAMES)

    # Filter to Levant-geolocated articles
    latlon_series = df["v2locations"].map(_levant_latlon)
    mask = latlon_series.notna()
    df = df[mask].copy()
    if df.empty:
        return pd.DataFrame(columns=GKG_NAMES)

    df["lat"] = [ll[0] for ll in latlon_series[mask]]
    df["lon"] = [ll[1] for ll in latlon_series[mask]]

    # Deduplicate by URL to avoid double-counting syndicated articles
    df = df.drop_duplicates(subset=["url"])
    return df


def _aggregate_gkg(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate GKG records to hex-level emotional and crisis features."""
    if df.empty or "lat" not in df.columns:
        return pd.DataFrame()

    df = df.copy()
    df["h3_id"] = [h3.latlng_to_cell(lat, lon, H3_RESOLUTION)
                   for lat, lon in zip(df["lat"], df["lon"])]

    gcam_parsed = df["v2gcam"].map(_parse_gcam)
    # Extract each dimension individually to avoid lambda closure bug
    df["gdelt_fear_score"]    = gcam_parsed.map(lambda d: d.get("gdelt_fear_score",    np.nan))
    df["gdelt_anger_score"]   = gcam_parsed.map(lambda d: d.get("gdelt_anger_score",   np.nan))
    df["gdelt_anxiety_score"] = gcam_parsed.map(lambda d: d.get("gdelt_anxiety_score", np.nan))

    df["gdelt_crisislex_count"] = df["v2themes"].map(_crisislex_count)
    df["gdelt_arabic_count"]    = df["trans_info"].map(_is_arabic).astype(int)

    return df.groupby("h3_id").agg(
        gdelt_fear_score      = ("gdelt_fear_score",      "mean"),
        gdelt_anger_score     = ("gdelt_anger_score",     "mean"),
        gdelt_anxiety_score   = ("gdelt_anxiety_score",   "mean"),
        gdelt_crisislex_count = ("gdelt_crisislex_count", "sum"),
        gdelt_arabic_count    = ("gdelt_arabic_count",    "sum"),
    ).reset_index()


# ── Main ingest ───────────────────────────────────────────────────────────────

def ingest_gdelt(date_str: str | None = None, backfill: bool = False,
                  skip_gkg: bool = False):
    """Ingest GDELT for the Levant and append results to the hex-daily parquet.

    Args:
        date_str:  ISO date string. Defaults to yesterday.
        backfill:  If True, process all dates from 2020-01-01 to yesterday.
        skip_gkg:  If True, skip the GKG stream (events only, much faster).
    """
    if backfill:
        yesterday = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        dates = pd.date_range("2020-01-01", yesterday).strftime("%Y-%m-%d").tolist()
    else:
        if date_str is None:
            date_str = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        dates = [date_str]

    if os.path.exists(OUTPUT):
        existing = pd.read_parquet(OUTPUT)
        done_dates = set(existing["date"].astype(str))
    else:
        existing = pd.DataFrame()
        done_dates = set()

    gkg_cols = [
        "gdelt_fear_score", "gdelt_anger_score", "gdelt_anxiety_score",
        "gdelt_crisislex_count", "gdelt_arabic_count",
    ]
    new_rows = []

    for d in dates:
        if d in done_dates:
            continue

        print(f"Processing {d}...")

        evt_df  = _fetch_events(d)
        hex_evt = _aggregate_events(evt_df)
        print(f"  Events: {len(evt_df)} Levant events → {len(hex_evt)} hexes")

        if hex_evt.empty:
            continue

        if not skip_gkg:
            gkg_df  = _fetch_gkg(d)
            hex_gkg = _aggregate_gkg(gkg_df)
            print(f"  GKG:    {len(gkg_df)} Levant articles → {len(hex_gkg)} hexes")
            day_df = hex_evt.merge(hex_gkg, on="h3_id", how="left")
        else:
            day_df = hex_evt.copy()

        # Fill GKG columns with 0 for hexes with no GKG data
        for col in gkg_cols:
            if col not in day_df.columns:
                day_df[col] = 0.0
        day_df[gkg_cols] = day_df[gkg_cols].fillna(0.0)

        day_df["date"] = pd.Timestamp(d)
        new_rows.append(day_df)

    if not new_rows:
        print("No new dates to process.")
        return

    new_df   = pd.concat(new_rows, ignore_index=True)
    combined = pd.concat([existing, new_df], ignore_index=True)
    combined = combined.drop_duplicates(subset=["h3_id", "date"], keep="last")
    combined = combined.sort_values(["h3_id", "date"]).reset_index(drop=True)

    os.makedirs(DATA_DIR, exist_ok=True)
    combined.to_parquet(OUTPUT, index=False)
    print(f"Saved {len(combined)} rows → {OUTPUT}")
    new_feature_cols = [c for c in combined.columns
                        if c not in ("h3_id", "date")]
    print(f"  Columns ({len(new_feature_cols)}): {', '.join(new_feature_cols)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GDELT events + GKG ingest for Levant")
    parser.add_argument("--date", help="Date to process (YYYY-MM-DD). Default: yesterday.")
    parser.add_argument("--backfill", action="store_true",
                        help="Process all dates from 2020-01-01 to yesterday.")
    parser.add_argument("--skip-gkg", action="store_true",
                        help="Skip GKG download. Events only (much faster).")
    args = parser.parse_args()
    ingest_gdelt(date_str=args.date, backfill=args.backfill,
                  skip_gkg=args.skip_gkg)
