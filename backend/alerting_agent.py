"""
Alerting Agent — Gemini-powered push notification text generator
=================================================================
Called by 05_score_live.py ONLY when a hex reaches DANGER tier.
Returns 2-3 sentences of human-readable alert text explaining the risk.

Uses google-genai SDK with gemini-2.5-flash.
"""

import os
from google import genai
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not set in backend/.env")
        _client = genai.Client(api_key=api_key)
    return _client


def generate_alert(features: dict) -> str:
    """
    Generate a 2-3 sentence tactical alert for a DANGER-tier hex.

    Parameters
    ----------
    features : dict
        Row from the feature table (or a subset). Keys that improve quality:
        h3_id, tactical_triggers, tactical_score, strategic_score,
        firms_hotspot_count, firms_max_frp, gdelt_hostility,
        gdelt_min_goldstein, event_velocity, neighbor_event_avg,
        total_fatalities, event_count.

    Returns
    -------
    str  2-3 sentence alert or empty string on failure.
    """
    triggers  = features.get("tactical_triggers", "Multiple risk signals detected")
    t_score   = features.get("tactical_score", 0.0)
    s_score   = features.get("strategic_score", 0.0)
    fatalities = int(features.get("total_fatalities", 0))
    hotspots  = int(features.get("firms_hotspot_count", 0))
    hostility = features.get("gdelt_hostility", 0.0)
    velocity  = features.get("event_velocity", 1.0)
    h3_id     = features.get("h3_id", "this area")

    prompt = f"""You are a conflict early warning analyst. Write a concise 2-3 sentence alert
for civilians in a high-risk area in the Levant region (Lebanon/Israel/Syria).

Current threat indicators for hex {h3_id}:
- Tactical risk score: {t_score:.2f}/1.0 (DANGER tier)
- Strategic (ML) escalation probability: {s_score:.2f}/1.0
- Active triggers: {triggers}
- Recent fatalities in area: {fatalities}
- Thermal hotspots detected: {hotspots}
- News hostility index: {hostility:.2f}/1.0
- Event velocity (vs 4-week avg): {velocity:.1f}x

Write a clear, factual alert in plain English. Do NOT name specific towns or claim
precise knowledge you don't have. Focus on the nature of the risk and recommended
caution. Keep it under 60 words. No bullet points."""

    try:
        client = _get_client()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        print(f"  Gemini alert generation failed: {e}")
        return ""


def explain_hex(hex_data: dict, lat: float, lng: float) -> str:
    """
    Generate a plain-English narrative for a hex using Gemini.
    Uses the hex's coordinates and risk signals to produce a human-readable
    situation summary grounded in Gemini's knowledge of the region.

    Parameters
    ----------
    hex_data : dict  Full risk_scores row (strategic_score, strategic_tier,
                     tactical_triggers, etc.)
    lat, lng : float  Geographic center of the hex.

    Returns
    -------
    str  2-4 sentence narrative or empty string on failure.
    """
    triggers   = hex_data.get("tactical_triggers", "") or ""
    s_score    = hex_data.get("strategic_score", 0.0)
    s_tier     = (hex_data.get("strategic_tier") or "green").upper()
    alert_text = hex_data.get("alert_text", "") or ""

    trigger_lines = [t.strip() for t in triggers.split("|") if t.strip()
                     and "No significant" not in t]

    trigger_block = ""
    if trigger_lines:
        trigger_block = "What our sensors detected:\n" + "\n".join(f"- {t}" for t in trigger_lines)
    else:
        trigger_block = "No immediate sensor triggers, but the area has elevated historical conflict patterns."

    prompt = f"""You are a conflict intelligence analyst briefing a civilian traveler.

Location: approximately {lat:.3f}°N, {lng:.3f}°E (Middle East / Levant region)
Risk level: {s_tier} (ML model gives {s_score:.0%} probability of dangerous event in next 72 hours)

{trigger_block}

Write 2-3 sentences in plain, human language that:
1. Identify the specific place (city, district, or border region) at these coordinates
2. Explain what the risk signals mean in plain terms — no numbers or acronyms
3. Summarize recent conflict context you know about this area and what a civilian should be aware of

Be factual, direct, and grounded. Do not use bullet points or headers."""

    try:
        client = _get_client()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        print(f"  Gemini explain_hex failed: {e}")
        if alert_text:
            return alert_text
        if trigger_lines:
            return f"Risk signals detected near this location: {'; '.join(trigger_lines[:2])}."
        return f"This area carries a {s_tier.lower()} risk level based on historical conflict patterns in the region."


# ── Quick self-test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_features = {
        "h3_id": "8623925ffffffff",
        "tactical_score": 0.82,
        "strategic_score": 0.78,
        "tactical_triggers": "Thermal spike detected (5 hotspots, max FRP=80 MW) | Hostile media coverage (hostility=0.75) | ML model flagged Red",
        "total_fatalities": 12,
        "firms_hotspot_count": 5,
        "gdelt_hostility": 0.75,
        "event_velocity": 3.5,
    }

    print("Generating test alert...")
    text = generate_alert(test_features)
    if text:
        print(f"\nAlert text:\n{text}")
    else:
        print("No alert generated (check GEMINI_API_KEY in backend/.env)")
