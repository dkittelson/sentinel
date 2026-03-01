"""
Alerting Agent — Gemini-powered push notification text generator
=================================================================
Called by 05_score_live.py ONLY when a hex reaches DANGER tier.
Returns 2-3 sentences of human-readable alert text explaining the risk.

Uses google-genai SDK with gemini-2.0-flash (free quota, fast).
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
            model="gemini-2.0-flash",
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        print(f"  Gemini alert generation failed: {e}")
        return ""


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
