"""
cluster_narrative.py — Hex Cluster Grouping + Shared Gemini Narratives
========================================================================
When a user clicks a hex, we find all adjacent hexes with the same strategic
tier (BFS flood-fill using H3 ring-1 neighbors) and generate ONE shared
Gemini narrative for the entire cluster.  This avoids redundant API calls
for hexes that are right next to each other showing the same risk level.

Cache key: frozenset of h3_ids in cluster → narrative text.
"""

import os
import sys
import h3
from typing import Optional
from functools import lru_cache

sys.path.insert(0, os.path.dirname(__file__))

# In-memory cache: cluster_key → narrative string
_narrative_cache: dict[str, str] = {}


def find_cluster(h3_id: str, hex_lookup: dict[str, dict], max_size: int = 30) -> list[str]:
    """
    BFS flood-fill from h3_id to find all contiguous hexes with the same
    strategic_tier. Uses ring-1 H3 neighbors.

    Parameters
    ----------
    h3_id      : Starting hex ID
    hex_lookup : dict mapping h3_id → hex data dict (must have 'strategic_tier')
    max_size   : Cap cluster size to avoid huge Gemini prompts

    Returns
    -------
    list of h3_id strings in the cluster (always includes the starting hex)
    """
    if h3_id not in hex_lookup:
        return [h3_id]

    target_tier = hex_lookup[h3_id].get("strategic_tier", "green")
    visited = set()
    queue = [h3_id]
    cluster = []

    while queue and len(cluster) < max_size:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)

        # Check if this hex exists in our data AND matches the target tier
        if current in hex_lookup and hex_lookup[current].get("strategic_tier") == target_tier:
            cluster.append(current)
            # Add ring-1 neighbors to queue
            try:
                neighbors = h3.grid_ring(current, 1)
                for n in neighbors:
                    if n not in visited:
                        queue.append(n)
            except Exception:
                pass

    return cluster if cluster else [h3_id]


def _cluster_cache_key(cluster_ids: list[str], date: Optional[str] = None) -> str:
    """Generate a deterministic cache key for a cluster."""
    sorted_ids = sorted(cluster_ids)
    key = "|".join(sorted_ids)
    if date:
        key = f"{date}:{key}"
    return key


def aggregate_cluster_features(cluster_ids: list[str], hex_lookup: dict[str, dict]) -> dict:
    """
    Aggregate feature values across all hexes in a cluster for the Gemini prompt.
    """
    agg = {
        "hex_count": len(cluster_ids),
        "strategic_tier": "green",
        "avg_strategic_score": 0.0,
        "max_strategic_score": 0.0,
        "total_tactical_triggers": [],
        "avg_tactical_score": 0.0,
    }

    scores = []
    t_scores = []
    triggers = set()

    for hid in cluster_ids:
        data = hex_lookup.get(hid, {})
        s = data.get("strategic_score", 0)
        scores.append(s)
        t_scores.append(data.get("tactical_score", 0))
        t = data.get("tactical_triggers", "")
        if t:
            for trigger in t.split(" | "):
                trigger = trigger.strip()
                if trigger and "No significant" not in trigger:
                    triggers.add(trigger)

    if scores:
        agg["avg_strategic_score"] = sum(scores) / len(scores)
        agg["max_strategic_score"] = max(scores)
    if t_scores:
        agg["avg_tactical_score"] = sum(t_scores) / len(t_scores)

    agg["total_tactical_triggers"] = list(triggers)[:8]  # cap at 8 triggers

    # Take tier from the clicked hex (first in list)
    if cluster_ids and cluster_ids[0] in hex_lookup:
        agg["strategic_tier"] = hex_lookup[cluster_ids[0]].get("strategic_tier", "green")

    return agg


def get_cluster_center(cluster_ids: list[str]) -> tuple[float, float]:
    """Get the geographic center of a cluster."""
    lats, lngs = [], []
    for hid in cluster_ids:
        try:
            lat, lng = h3.cell_to_latlng(hid)
            lats.append(lat)
            lngs.append(lng)
        except Exception:
            pass
    if not lats:
        return 33.9, 35.5  # Beirut fallback
    return sum(lats) / len(lats), sum(lngs) / len(lngs)


def generate_cluster_narrative(
    h3_id: str,
    hex_lookup: dict[str, dict],
    date: Optional[str] = None,
) -> dict:
    """
    Find the cluster around h3_id, generate (or retrieve cached) a shared
    Gemini narrative, and return it along with cluster metadata.

    Returns
    -------
    dict with keys: narrative, cluster_ids, hex_count, center_lat, center_lng
    """
    # Find cluster
    cluster_ids = find_cluster(h3_id, hex_lookup)

    # Check cache
    cache_key = _cluster_cache_key(cluster_ids, date)
    if cache_key in _narrative_cache:
        lat, lng = get_cluster_center(cluster_ids)
        return {
            "narrative": _narrative_cache[cache_key],
            "cluster_ids": cluster_ids,
            "hex_count": len(cluster_ids),
            "center_lat": lat,
            "center_lng": lng,
            "cached": True,
        }

    # Aggregate cluster features
    agg = aggregate_cluster_features(cluster_ids, hex_lookup)
    lat, lng = get_cluster_center(cluster_ids)
    tier = agg["strategic_tier"].upper()

    trigger_block = ""
    if agg["total_tactical_triggers"]:
        trigger_block = "Active sensor signals across the cluster:\n" + \
            "\n".join(f"- {t}" for t in agg["total_tactical_triggers"])
    else:
        trigger_block = "No immediate sensor triggers, but historical conflict patterns are elevated."

    date_context = f" on {date}" if date else ""
    is_backtest = bool(date)

    # Map tier to human-readable danger description
    tier_desc = {
        "RED": "HIGH RISK — active conflict zone",
        "ORANGE": "ELEVATED RISK — significant danger present",
        "YELLOW": "MODERATE RISK — tensions detected",
        "GREEN": "LOW RISK — currently stable",
    }.get(tier, "UNKNOWN RISK")

    if is_backtest:
        time_instruction = (
            f"This is a HISTORICAL ANALYSIS for {date}. "
            f"Search for news and events that occurred AROUND {date} "
            f"(within a few days before and after). "
            f"Do NOT report today's current news — report what was happening at that specific point in history."
        )
        recency_phrase = f"around {date}"
        currency_phrase = "was happening"
    else:
        time_instruction = "Search the web for the LATEST news (last 48-72 hours)."
        recency_phrase = "in the last 48-72 hours"
        currency_phrase = "is currently happening"

    prompt = f"""You are a conflict intelligence analyst briefing a civilian traveler.
You have access to Google Search — USE IT to find relevant news.

Location: approximately {lat:.3f}°N, {lng:.3f}°E (Middle East / Levant region){date_context}
Our system rates this area: {tier_desc}
Cluster size: {agg['hex_count']} adjacent monitoring zones

{time_instruction}

IMPORTANT: Our system has classified this area as {tier}. Your job is to find NEWS that explains what is happening here. Do NOT contradict or downplay the risk level. If the area is rated RED or ORANGE, do not say it is "safe" or "low probability" — there is a reason our system flagged it.

INSTRUCTIONS:
1. Search the web for news {recency_phrase} about conflict, violence, military operations, protests, or security incidents near these coordinates.
2. Identify the specific area (city, district, border region).
3. Write 3-5 sentences summarizing what {currency_phrase} based on what you found in the news. Focus on FACTS from news sources.
4. Explain what makes (or made) this area dangerous or tense based on what you found.
5. If the cluster spans {agg['hex_count']} zones, note whether the danger is widespread or localized.

Be factual, direct, concise. No bullet points, no headers, no raw numbers. Write in plain language for a civilian."""

    # Call Gemini
    try:
        import re
        from alerting_agent import _get_client
        from google.genai import types

        client = _get_client()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
        text = response.text.strip()
        text = re.sub(r'\[\d+\]', '', text).strip()
        narrative = text
    except Exception as e:
        print(f"  [cluster] Gemini failed: {e}")
        # Fallback
        try:
            from alerting_agent import _get_client
            client = _get_client()
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            narrative = response.text.strip()
        except Exception as e2:
            print(f"  [cluster] Fallback also failed: {e2}")
            if agg["total_tactical_triggers"]:
                narrative = f"This {tier.lower()}-risk cluster of {agg['hex_count']} zones shows: {'; '.join(agg['total_tactical_triggers'][:3])}."
            else:
                narrative = f"This area carries a {tier.lower()} risk level across {agg['hex_count']} adjacent monitoring zones based on historical conflict patterns."

    # Cache it
    _narrative_cache[cache_key] = narrative

    return {
        "narrative": narrative,
        "cluster_ids": cluster_ids,
        "hex_count": len(cluster_ids),
        "center_lat": lat,
        "center_lng": lng,
        "cached": False,
    }


def clear_cache():
    """Clear the narrative cache (e.g. on new scoring run)."""
    global _narrative_cache
    _narrative_cache = {}
