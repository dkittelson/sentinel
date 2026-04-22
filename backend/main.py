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

from fastapi import FastAPI, HTTPException, Query, Header
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

ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:5174").split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
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
            # Tiers are already set by the scorer using percentile thresholds
            # calibrated to the latest run's distribution. Don't re-tierify here.
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

    # Final fallback: static demo dataset bundled with the repo
    import json as _json
    demo_path = os.path.join(os.path.dirname(__file__), "demo_hexes.json")
    try:
        with open(demo_path) as f:
            print("[hexes] Serving static demo dataset")
            return _json.load(f)
    except Exception as e2:
        print(f"[hexes] Demo fallback also failed: {e2}")
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


@app.get("/hex/{h3_id}/drivers")
def get_hex_drivers(h3_id: str):
    """
    Return the top driver chips for a hex — 'why is this hex orange?'
    Parses tactical_triggers + annotates with feature context from GDELT/FIRMS.
    Used by HexSidebar to show 'What's driving this score?' chips.
    """
    risk = (
        supabase.table("risk_scores")
        .select("strategic_score, strategic_tier, tactical_tier, tactical_triggers, should_alert")
        .eq("h3_id", h3_id)
        .maybe_single()
        .execute()
    )
    if not risk.data:
        return {"drivers": [], "score": None, "tier": "green"}

    row = risk.data
    score = row.get("strategic_score", 0) or 0
    tier  = row.get("strategic_tier", "green")
    raw   = row.get("tactical_triggers", "") or ""

    # Parse pipe-separated tactical triggers into structured chips
    raw_triggers = [t.strip() for t in raw.split("|") if t.strip()]

    # Map trigger text → chip metadata (label, severity color)
    TRIGGER_MAP = {
        "hostility":     ("Media hostility surge",   "#e74c3c"),
        "firms":         ("Thermal anomaly (fire)",  "#f39c12"),
        "fire":          ("Thermal anomaly (fire)",  "#f39c12"),
        "siren":         ("Air raid sirens detected","#e74c3c"),
        "neighbor":      ("Spillover from adjacent", "#f09438"),
        "gdelt":         ("Media signal spike",      "#f09438"),
        "fatality":      ("Fatality surge",          "#c0392b"),
        "explosion":     ("Explosions reported",     "#e74c3c"),
        "battle":        ("Active battle events",    "#c0392b"),
        "actor":         ("New armed actor",         "#8e44ad"),
        "strategic":     ("High ML risk score",      "#e74c3c"),
        "danger":        ("Sustained danger level",  "#e74c3c"),
        "economic":      ("Economic stress signal",  "#f09438"),
        "lbp":           ("Currency volatility",     "#f09438"),
    }

    drivers = []
    seen_labels = set()
    for trigger in raw_triggers:
        tl = trigger.lower()
        for keyword, (label, color) in TRIGGER_MAP.items():
            if keyword in tl and label not in seen_labels:
                drivers.append({"label": label, "color": color, "raw": trigger})
                seen_labels.add(label)
                break
        else:
            if trigger and trigger not in seen_labels:
                drivers.append({"label": trigger, "color": "#888", "raw": trigger})
                seen_labels.add(trigger)

    # Score-based driver if no triggers found but score is elevated
    if not drivers and score >= 0.54:
        tier_colors = {"red": "#e74c3c", "orange": "#f09438", "yellow": "#f1c40f"}
        drivers.append({
            "label": f"ML score {score:.2f} — {tier} alert",
            "color": tier_colors.get(tier, "#888"),
            "raw": "strategic_score",
        })

    return {
        "drivers": drivers[:5],  # cap at 5 chips
        "score": round(score, 4),
        "tier": tier,
    }


@app.get("/hex/{h3_id}/history")
def get_hex_history(
    h3_id: str,
    days: int = Query(14, description="How many days of history to return", ge=1, le=90),
):
    """
    Return daily strategic_score history for a hex.
    Powers the 14-day sparkline + trend projection in HexSidebar.

    Query order:
    1. risk_scores_history table (real scored data, accumulates after migration)
    2. Backtest engine fallback for any days not yet in the history table
       (uses the same CSV + v1 XGBoost model that powers /hexes/backtest)
    """
    import datetime

    cutoff = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).isoformat()

    # 1. Pull from history table
    resp = (
        supabase.table("risk_scores_history")
        .select("strategic_score, strategic_tier, scored_at")
        .eq("h3_id", h3_id)
        .gte("scored_at", cutoff)
        .order("scored_at", desc=False)
        .execute()
    )

    # Collapse multiple intra-day runs to one point per calendar day (last run wins)
    from collections import OrderedDict
    by_day: dict = OrderedDict()
    for row in (resp.data or []):
        day = row["scored_at"][:10]   # "YYYY-MM-DD"
        by_day[day] = {
            "date":            day,
            "strategic_score": round(row["strategic_score"], 4),
            "strategic_tier":  row["strategic_tier"],
        }

    # 2. Backtest fallback for missing days (history table starts empty after migration)
    present_days = set(by_day.keys())
    today = datetime.date.today()
    needed_days = [
        str(today - datetime.timedelta(days=i))
        for i in range(days - 1, -1, -1)
    ]
    missing = [d for d in needed_days if d not in present_days]

    if missing:
        try:
            sys.path.insert(0, os.path.dirname(__file__))
            from backtest_score import score_date
            for day_str in missing:
                records = score_date(day_str)
                match = next((r for r in records if r["h3_id"] == h3_id), None)
                if match:
                    by_day[day_str] = {
                        "date":            day_str,
                        "strategic_score": round(match["strategic_score"], 4),
                        "strategic_tier":  match["strategic_tier"],
                    }
        except Exception as e:
            print(f"[history] Backtest fallback failed for {h3_id}: {e}")

    # Return sorted ascending
    result = sorted(by_day.values(), key=lambda x: x["date"])
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

    # Aggregate stats using STRATEGIC scores (matches the heatmap the user sees)
    # Recompute strategic tier from score using same thresholds as frontend
    strategic_tiers = {"RED": 0, "ORANGE": 0, "YELLOW": 0, "GREEN": 0}
    all_triggers = []
    latest_scored_at = None

    for s in scores:
        sc = s.get("strategic_score", 0) or 0
        if sc >= 0.70:
            strategic_tiers["RED"] += 1
        elif sc >= 0.63:
            strategic_tiers["ORANGE"] += 1
        elif sc >= 0.54:
            strategic_tiers["YELLOW"] += 1
        else:
            strategic_tiers["GREEN"] += 1
        if s.get("tactical_triggers"):
            all_triggers.extend(s["tactical_triggers"].split(" | "))
        if s.get("scored_at") and (not latest_scored_at or s["scored_at"] > latest_scored_at):
            latest_scored_at = s["scored_at"]

    # Deduplicate triggers, keep most frequent
    from collections import Counter
    trigger_counts = Counter(t.strip() for t in all_triggers if t.strip())
    top_triggers = [t for t, _ in trigger_counts.most_common(5)]

    avg_strategic = sum(s.get("strategic_score", 0) for s in scores) / len(scores)
    max_strategic = max((s.get("strategic_score", 0) for s in scores), default=0)

    # Build Gemini prompt — combines ML data with live web search for grounding
    # Gemini will search the web (news, X/Twitter, etc.) and cite sources
    prompt = f"""You are a conflict intelligence analyst providing a situational briefing for aid workers and civilians.
You have access to Google Search. SEARCH for the latest news, social media posts (X/Twitter, Instagram), and reports about conflict, violence, military operations, and security incidents in this region.

AREA: Levant corridor — approximate center {lat:.1f}°N, {lon:.1f}°E (covers Lebanon, Israel, Syria, and broader Middle East)

OUR ML MODEL'S 72-HOUR RISK FORECAST for this map view ({len(scores)} hexes monitored):
- RED (high risk, score ≥ 0.70): {strategic_tiers['RED']} hexes
- ORANGE (elevated risk, score 0.63-0.70): {strategic_tiers['ORANGE']} hexes
- YELLOW (moderate risk, score 0.54-0.63): {strategic_tiers['YELLOW']} hexes
- GREEN/CLEAR (low risk, score < 0.54): {strategic_tiers['GREEN']} hexes
- Average danger probability: {avg_strategic:.3f} | Peak: {max_strategic:.3f}

ACTIVE SIGNALS FROM OUR SENSORS:
{chr(10).join(f'- {t}' for t in top_triggers) if top_triggers else '- No significant signals'}

INSTRUCTIONS:
1. Search for the LATEST news (last 48 hours) about conflict, violence, airstrikes, shelling, protests, or military movements in this region.
2. Write a 4-5 sentence briefing that COMBINES our ML risk data above with what you find from current news/social media.
3. Explain WHY certain areas might be RED or ORANGE — connect the ML scores to real events you find.
4. At the end, add a "Sources:" section listing 2-4 of the most relevant articles/posts you found, each on its own line with the outlet name and title.
5. Be factual and calm. Use plain language for civilians. Do NOT say the area is safe or low-risk if RED or ORANGE hexes are present."""

    briefing = "Conflict intelligence data aggregated. Gemini API unavailable."
    citations = []
    try:
        from google import genai as _genai
        import google.genai.types as _types
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            gclient = _genai.Client(api_key=gemini_key)
            response = gclient.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=_types.GenerateContentConfig(
                    tools=[_types.Tool(google_search=_types.GoogleSearch())],
                    thinking_config=_types.ThinkingConfig(thinking_budget=1024),
                ),
            )
            briefing = response.text.strip()

            # Extract grounding citations from response metadata
            cands = response.candidates
            if cands and cands[0].grounding_metadata:
                gm = cands[0].grounding_metadata
                if gm.grounding_chunks:
                    seen_domains = set()
                    for chunk in gm.grounding_chunks:
                        if chunk.web and chunk.web.uri:
                            domain = chunk.web.title or chunk.web.uri
                            if domain not in seen_domains:
                                seen_domains.add(domain)
                                citations.append({
                                    "title": chunk.web.title or "Source",
                                    "url": chunk.web.uri,
                                })
    except Exception as e:
        print(f"[area-summary] Gemini failed: {e}")

    return {
        "briefing": briefing,
        "hex_count": len(scores),
        "tier_counts": strategic_tiers,
        "top_triggers": top_triggers,
        "citations": citations,
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
def trigger_ingest(x_api_key: str = Header(None)):
    """Manually trigger a scoring run (useful for demos / testing)."""
    api_key = os.getenv("SENTINEL_API_KEY")
    if api_key and x_api_key != api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from importlib import import_module, invalidate_caches
        invalidate_caches()
        scorer = import_module("05_score_live")
        records = scorer.run_scoring()
        return {"status": "ok", "hexes_scored": len(records)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
