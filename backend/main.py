"""
Sentinel FastAPI Backend
========================
Endpoints:
  GET  /health                            → liveness check
  GET  /hexes                             → all hex IDs + current risk scores
  GET  /hex/{h3_id}                       → full risk breakdown for one hex
  GET  /hexes/region?lat=&lon=&radius_km= → spatial query via PostGIS ST_Distance
  POST /ingest/run                        → manually trigger a scoring run

APScheduler fires a scoring run every 15 minutes on startup.

Run from sentinel/ root:
    cd sentinel && uvicorn backend.main:app --reload
"""

import os
import sys
import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    sys.exit("SUPABASE_URL and SUPABASE_KEY must be set in backend/.env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ── APScheduler ───────────────────────────────────────────────────────────────
scheduler = BackgroundScheduler()


def scoring_job():
    """Cron job: run scoring engine every 15 minutes."""
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from importlib import import_module
        scorer = import_module("05_score_live")
        scorer.run_scoring()
    except Exception as e:
        print(f"[scheduler] Scoring job failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(scoring_job, "interval", minutes=15, id="scoring")
    scheduler.start()
    print("[startup] APScheduler started — scoring every 15 minutes")
    yield
    scheduler.shutdown()


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="Sentinel", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten for production
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/hexes")
def get_all_hexes():
    """
    Return all scored hexes with their current risk state.
    Frontend polls this every 30s to update the map layer.

    Falls back to backtest engine (latest available date from CSV) when
    Supabase has no scored data — enables instant "live" mode without
    requiring 05_score_live.py to have pushed to Supabase.
    """
    try:
        # Supabase default limit is 1000 — fetch all scored hexes
        all_rows = []
        page_size = 1000
        offset = 0
        while True:
            resp = (
                supabase.table("risk_scores")
                .select(
                    "h3_id, strategic_score, strategic_tier, "
                    "tactical_score, tactical_tier, should_alert, scored_at"
                )
                .range(offset, offset + page_size - 1)
                .execute()
            )
            if resp.data:
                all_rows.extend(resp.data)
            if not resp.data or len(resp.data) < page_size:
                break
            offset += page_size
        if all_rows:
            # Recompute tiers on-the-fly so threshold changes take effect
            # without re-running the full scoring pipeline
            for row in all_rows:
                s = row.get("strategic_score", 0)
                if s >= 0.70:
                    row["strategic_tier"] = "red"
                elif s >= 0.63:
                    row["strategic_tier"] = "orange"
                elif s >= 0.54:
                    row["strategic_tier"] = "yellow"
                else:
                    row["strategic_tier"] = "green"
            return all_rows
    except Exception as e:
        print(f"[hexes] Supabase query failed, falling back to CSV: {e}")

    # Fallback: score the latest available date from the processed CSV
    try:
        from backtest_score import score_date, get_date_range
        date_range = get_date_range()
        latest = date_range["max_date"]
        print(f"[hexes] Supabase empty — scoring latest CSV date: {latest}")
        return score_date(latest)
    except Exception as e:
        print(f"[hexes] Backtest fallback also failed: {e}")
        return []


@app.get("/hex/{h3_id}")
def get_hex(h3_id: str):
    """
    Full risk breakdown for a single hex (shown in sidebar on click).
    Includes risk scores, tactical triggers, Gemini alert text, and
    the most recent GDELT/FIRMS signals.
    """
    # risk_scores row
    risk = (
        supabase.table("risk_scores")
        .select("*")
        .eq("h3_id", h3_id)
        .maybe_single()
        .execute()
    )
    if not risk.data:
        raise HTTPException(status_code=404, detail=f"Hex {h3_id} not found")

    result = dict(risk.data)

    # Most recent GDELT signal
    gdelt = (
        supabase.table("gdelt_signals")
        .select("*")
        .eq("h3_id", h3_id)
        .order("week", desc=True)
        .limit(1)
        .execute()
    )
    result["gdelt"] = gdelt.data[0] if gdelt.data else None

    # Most recent FIRMS anomaly
    firms = (
        supabase.table("firms_anomalies")
        .select("*")
        .eq("h3_id", h3_id)
        .order("week", desc=True)
        .limit(1)
        .execute()
    )
    result["firms"] = firms.data[0] if firms.data else None

    # Last 4 ACLED events
    acled = (
        supabase.table("acled_events")
        .select("event_date, event_type, fatalities, actor1")
        .eq("h3_id", h3_id)
        .order("event_date", desc=True)
        .limit(4)
        .execute()
    )
    result["recent_events"] = acled.data

    return result


@app.get("/hex/{h3_id}/narrative")
def get_hex_narrative(h3_id: str):
    """
    LLM narrative for a hex: plain-English situation summary from Gemini.
    """
    try:
        import h3 as h3lib
        sys.path.insert(0, os.path.dirname(__file__))
        from alerting_agent import explain_hex

        risk = (
            supabase.table("risk_scores")
            .select("*")
            .eq("h3_id", h3_id)
            .maybe_single()
            .execute()
        )
        if not risk.data:
            return {"h3_id": h3_id, "narrative": ""}

        lat, lng = h3lib.cell_to_latlng(h3_id)
        narrative = explain_hex(risk.data, lat, lng)
        return {"h3_id": h3_id, "narrative": narrative}
    except Exception as e:
        print(f"[narrative] Error for {h3_id}: {e}")
        return {"h3_id": h3_id, "narrative": ""}


@app.get("/hexes/region")
def get_hexes_region(
    lat: float = Query(..., description="Center latitude"),
    lon: float = Query(..., description="Center longitude"),
    radius_km: float = Query(50.0, description="Search radius in kilometers"),
):
    """
    Return all scored hexes within radius_km of the given GPS point.
    Uses PostGIS ST_DWithin on hex_grid.centroid.
    """
    radius_m = radius_km * 1000

    # Call Supabase RPC function (must be created in Supabase SQL editor — see below)
    resp = supabase.rpc(
        "hexes_near_point",
        {"center_lat": lat, "center_lon": lon, "radius_m": radius_m},
    ).execute()

    if not resp.data:
        return []

    # Enrich with risk scores
    h3_ids = [row["h3_id"] for row in resp.data]
    scores = (
        supabase.table("risk_scores")
        .select(
            "h3_id, strategic_score, strategic_tier, "
            "tactical_score, tactical_tier, should_alert"
        )
        .in_("h3_id", h3_ids)
        .execute()
    )

    scores_by_id = {r["h3_id"]: r for r in scores.data}
    for row in resp.data:
        row.update(scores_by_id.get(row["h3_id"], {}))

    return resp.data


@app.get("/area-summary")
def get_area_summary(
    lat: float = Query(..., description="Center latitude of map view"),
    lon: float = Query(..., description="Center longitude of map view"),
    radius_km: float = Query(80.0, description="Visible radius in km"),
):
    """
    Generate a Gemini LLM briefing for the conflict situation in the visible map area.
    Called by the NewsSidebar whenever the user pans/zooms.
    """
    radius_m = radius_km * 1000

    # Get hexes in view
    geo_resp = supabase.rpc(
        "hexes_near_point",
        {"center_lat": lat, "center_lon": lon, "radius_m": radius_m},
    ).execute()

    nearby_ids = [r["h3_id"] for r in (geo_resp.data or [])]

    if not nearby_ids:
        return {
            "briefing": "No monitored hexes in this area.",
            "hex_count": 0,
            "tier_counts": {},
            "top_triggers": [],
            "scored_at": None,
        }

    # Get risk scores for those hexes
    scores_resp = (
        supabase.table("risk_scores")
        .select("h3_id, tactical_tier, tactical_score, strategic_score, tactical_triggers, scored_at")
        .in_("h3_id", nearby_ids)
        .execute()
    )
    scores = scores_resp.data or []

    if not scores:
        return {
            "briefing": "No risk scores available yet for this area. Run the scoring engine first.",
            "hex_count": len(nearby_ids),
            "tier_counts": {},
            "top_triggers": [],
            "scored_at": None,
        }

    # Aggregate stats
    tier_counts = {"DANGER": 0, "WARNING": 0, "WATCH": 0, "CLEAR": 0}
    all_triggers = []
    latest_scored_at = None

    for s in scores:
        tier = s.get("tactical_tier", "CLEAR")
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
        if s.get("tactical_triggers"):
            all_triggers.extend(s["tactical_triggers"].split(" | "))
        if s.get("scored_at") and (not latest_scored_at or s["scored_at"] > latest_scored_at):
            latest_scored_at = s["scored_at"]

    # Deduplicate triggers, keep most frequent
    from collections import Counter
    trigger_counts = Counter(t.strip() for t in all_triggers if t.strip())
    top_triggers = [t for t, _ in trigger_counts.most_common(5)]

    avg_tactical = sum(s.get("tactical_score", 0) for s in scores) / len(scores)
    avg_strategic = sum(s.get("strategic_score", 0) for s in scores) / len(scores)

    # Build Gemini prompt
    prompt = f"""You are a conflict intelligence analyst providing a situational briefing for aid workers and civilians.

Area: Levant region (Lebanon / northern Israel / southern Syria)
Hexes monitored in current map view: {len(scores)}

Risk distribution:
- DANGER (immediate risk): {tier_counts['DANGER']} hexes
- WARNING (elevated risk): {tier_counts['WARNING']} hexes
- WATCH (moderate risk):   {tier_counts['WATCH']} hexes
- CLEAR (low risk):        {tier_counts['CLEAR']} hexes

Average tactical score: {avg_tactical:.2f}/1.0
Average ML escalation probability: {avg_strategic:.2f}/1.0

Most common active signals in this area:
{chr(10).join(f'- {t}' for t in top_triggers) if top_triggers else '- No significant signals'}

Write a 3-4 sentence conflict briefing for this area. Be factual, calm, and specific about the nature of risks detected.
Do not name specific towns. Do not speculate beyond the data. Use plain language suitable for civilians.
End with one practical sentence of general guidance."""

    briefing = "Conflict intelligence data aggregated. Gemini API unavailable."
    try:
        from google import genai as _genai
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            gclient = _genai.Client(api_key=gemini_key)
            response = gclient.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )
            briefing = response.text.strip()
    except Exception as e:
        print(f"[area-summary] Gemini failed: {e}")

    return {
        "briefing": briefing,
        "hex_count": len(scores),
        "tier_counts": tier_counts,
        "top_triggers": top_triggers,
        "scored_at": latest_scored_at,
    }


@app.get("/hexes/backtest")
def backtest_hexes(
    date: str = Query(..., description="Date to score (YYYY-MM-DD)"),
):
    """
    Score all hexes for a historical date using the production model.
    Powers the demo time-slider — no Supabase writes.
    """
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from backtest_score import score_date
        records = score_date(date)
        return records
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/backtest/date-range")
def backtest_date_range():
    """Return the min/max dates available for backtesting."""
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from backtest_score import get_date_range
        return get_date_range()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/hex/{h3_id}/cluster-narrative")
def get_cluster_narrative(
    h3_id: str,
    date: Optional[str] = Query(None, description="Date for backtest mode (YYYY-MM-DD)"),
):
    """
    Generate a Gemini narrative shared across all adjacent hexes with the same
    strategic tier (cluster).  Returns the narrative + list of cluster hex IDs
    so the frontend can highlight the whole cluster.
    """
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from cluster_narrative import generate_cluster_narrative

        # Build hex_lookup from backtest or live data
        if date:
            from backtest_score import score_date
            records = score_date(date)
        else:
            resp = (
                supabase.table("risk_scores")
                .select("h3_id, strategic_score, strategic_tier, tactical_score, tactical_tier, tactical_triggers")
                .execute()
            )
            records = resp.data or []

        hex_lookup = {r["h3_id"]: r for r in records}

        result = generate_cluster_narrative(h3_id, hex_lookup, date)
        return result
    except Exception as e:
        print(f"[cluster-narrative] Error: {e}")
        return {"narrative": "", "cluster_ids": [h3_id], "hex_count": 1, "error": str(e)}


@app.get("/evac-route")
def get_evac_route(
    from_lat: float = Query(..., description="Starting latitude"),
    from_lng: float = Query(..., description="Starting longitude"),
    to_lat: Optional[float] = Query(None, description="Destination latitude (auto if omitted)"),
    to_lng: Optional[float] = Query(None, description="Destination longitude (auto if omitted)"),
    date: Optional[str] = Query(None, description="Date for backtest mode (YYYY-MM-DD)"),
):
    """
    AI-powered evacuation route: finds safest path from a point, avoiding
    danger hexes.  Uses Gemini to generate a human-readable recommendation.
    Works for both live and backtest mode.
    """
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from evac_router import find_evac_route, generate_evac_narrative
        import json

        # Load shelter data
        shelter_path = os.path.join(
            os.path.dirname(__file__), "..", "frontend", "src", "data", "shelters.json"
        )
        shelter_data = []
        if os.path.exists(shelter_path):
            with open(shelter_path) as f:
                shelter_data = json.load(f).get("shelters", [])

        # Get current hex scores
        if date:
            from backtest_score import score_date
            hex_scores = score_date(date)
        else:
            resp = (
                supabase.table("risk_scores")
                .select("h3_id, strategic_score, strategic_tier")
                .execute()
            )
            hex_scores = resp.data or []

        hex_lookup = {r["h3_id"]: r for r in hex_scores}

        # Find route
        route = find_evac_route(
            from_lat, from_lng, hex_scores,
            to_lat=to_lat, to_lng=to_lng,
            shelter_data=shelter_data,
        )

        # Generate AI narrative
        route["narrative"] = generate_evac_narrative(route, hex_lookup)

        return route
    except Exception as e:
        print(f"[evac-route] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/shelters")
def get_shelters():
    """Return all known hospitals, UN shelters, and evacuation points."""
    import json
    shelter_path = os.path.join(
        os.path.dirname(__file__), "..", "frontend", "src", "data", "shelters.json"
    )
    try:
        with open(shelter_path) as f:
            return json.load(f)
    except Exception:
        return {"shelters": []}


@app.post("/ingest/run")
def trigger_ingest():
    """Manually trigger a scoring run (useful for demos / testing)."""
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from importlib import import_module, invalidate_caches
        invalidate_caches()
        scorer = import_module("05_score_live")
        records = scorer.run_scoring()
        return {"status": "ok", "hexes_scored": len(records)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
