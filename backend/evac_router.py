"""
evac_router.py — AI-Powered Evacuation Route Agent (v2 — Real Roads)
=====================================================================
Uses Mapbox Directions API for real road routing to the nearest safe city,
scores each route segment against hex danger zones + FIRMS thermal data,
and uses Gemini to narrate the recommendation.

Algorithm:
1. From user location, identify candidate safe destinations (cities/shelters
   NOT in RED hexes)
2. Call Mapbox Directions API for actual driving route
3. Check which hexes the route traverses — warn if any are RED
4. If too many danger hexes on route, try next-best destination
5. Return real road GeoJSON + distance + destination + Gemini narrative

Works for both live mode (current scores) and backtest mode (historical date).
"""

import os
import sys
import h3
import math
import json
import requests as _requests
from typing import Optional

sys.path.insert(0, os.path.dirname(__file__))

# Mapbox token — set MAPBOX_TOKEN in backend/.env
MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN", "")

# Safe destination cities: name, lat, lng — sorted roughly by region
# These represent cities/camps that a civilian could realistically evacuate to.
SAFE_DESTINATIONS = [
    # Lebanon
    {"name": "Beirut", "lat": 33.8938, "lng": 35.5018, "country": "Lebanon"},
    {"name": "Tripoli", "lat": 34.4367, "lng": 35.8497, "country": "Lebanon"},
    {"name": "Sidon", "lat": 33.5633, "lng": 35.3714, "country": "Lebanon"},
    {"name": "Jounieh", "lat": 33.9808, "lng": 35.6178, "country": "Lebanon"},
    {"name": "Zahle", "lat": 33.8463, "lng": 35.9020, "country": "Lebanon"},
    # Syria (interior / typically calmer areas)
    {"name": "Damascus", "lat": 33.5138, "lng": 36.2765, "country": "Syria"},
    {"name": "Latakia", "lat": 35.5317, "lng": 35.7918, "country": "Syria"},
    {"name": "Tartous", "lat": 34.8959, "lng": 35.8867, "country": "Syria"},
    {"name": "Homs", "lat": 34.7324, "lng": 36.7137, "country": "Syria"},
    # Jordan
    {"name": "Amman", "lat": 31.9454, "lng": 35.9284, "country": "Jordan"},
    {"name": "Irbid", "lat": 32.5568, "lng": 35.8469, "country": "Jordan"},
    {"name": "Mafraq", "lat": 32.3422, "lng": 36.2079, "country": "Jordan"},
    # Turkey (border)
    {"name": "Antakya (Hatay)", "lat": 36.2025, "lng": 36.1522, "country": "Turkey"},
    {"name": "Gaziantep", "lat": 37.0594, "lng": 37.3825, "country": "Turkey"},
    # Iraq (Kurdistan)
    {"name": "Erbil", "lat": 36.1912, "lng": 44.0089, "country": "Iraq"},
    # Israel
    {"name": "Haifa", "lat": 32.7940, "lng": 34.9896, "country": "Israel"},
]


def _haversine(lat1, lng1, lat2, lng2):
    """Haversine distance in km between two points."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _get_mapbox_route(from_lng, from_lat, to_lng, to_lat, waypoints=None):
    """
    Call Mapbox Directions API to get a driving route.
    Optionally pass waypoints as list of [lng, lat] to route via intermediate points
    (useful for routing around danger zones).
    Returns (route_coords, distance_km, duration_min) or (None, None, None).
    """
    coords_str = f"{from_lng},{from_lat}"
    if waypoints:
        for wp in waypoints:
            coords_str += f";{wp[0]},{wp[1]}"
    coords_str += f";{to_lng},{to_lat}"

    url = (
        f"https://api.mapbox.com/directions/v5/mapbox/driving/"
        f"{coords_str}"
        f"?geometries=geojson&overview=full&access_token={MAPBOX_TOKEN}"
    )
    try:
        resp = _requests.get(url, headers={"User-Agent": "Sentinel/1.0"}, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") != "Ok" or not data.get("routes"):
            return None, None, None

        route = data["routes"][0]
        coords = route["geometry"]["coordinates"]  # [[lng, lat], ...]
        distance_km = round(route["distance"] / 1000, 1)
        duration_min = round(route["duration"] / 60, 1)
        return coords, distance_km, duration_min
    except Exception as e:
        print(f"  [evac] Mapbox Directions API error: {e}")
        return None, None, None


def _score_route_safety(route_coords, hex_lookup, danger_hexes, firms_data=None):
    """
    Walk along route coords, check which H3 hexes they pass through.
    Returns (danger_hex_count, total_hexes_on_route, danger_hex_ids).
    """
    seen = set()
    danger_on_route = set()

    # Sample every ~5th point (routes can have hundreds of points)
    step = max(1, len(route_coords) // 100)
    for i in range(0, len(route_coords), step):
        lng, lat = route_coords[i]
        try:
            hid = h3.latlng_to_cell(lat, lng, 6)
        except Exception:
            continue
        if hid in seen:
            continue
        seen.add(hid)
        if hid in danger_hexes:
            danger_on_route.add(hid)

    return len(danger_on_route), len(seen), list(danger_on_route)


def find_evac_route(
    from_lat: float,
    from_lng: float,
    hex_scores: list[dict],
    to_lat: Optional[float] = None,
    to_lng: Optional[float] = None,
    shelter_data: Optional[list[dict]] = None,
) -> dict:
    """
    Find the safest evacuation route via real roads.

    1. Identify danger hexes (red + orange)
    2. Rank candidate destinations (cities/shelters NOT in danger hexes, closest first)
    3. Get Mapbox driving directions to top candidates
    4. Pick route with fewest danger hexes on path
    5. If route crosses danger zones, try alternative routing with offset waypoint
    6. Find nearest shelter near the destination

    Returns dict with route_points (GeoJSON coords), distance_km, destination, etc.
    """
    # Build hex lookup
    hex_lookup = {}
    for h in hex_scores:
        hid = h.get("h3_id")
        if hid:
            hex_lookup[hid] = h

    # Classify hexes by danger — red AND orange count as danger for routing
    danger_hexes = set()
    red_hexes = set()
    for hid, data in hex_lookup.items():
        tier = data.get("strategic_tier", "green")
        if tier == "red":
            danger_hexes.add(hid)
            red_hexes.add(hid)
        elif tier == "orange":
            danger_hexes.add(hid)

    # ---- Pick destination candidates ----
    if to_lat is not None and to_lng is not None:
        candidates = [{"name": "Custom destination", "lat": to_lat, "lng": to_lng, "country": ""}]
    else:
        # Combine safe destinations + shelters as possible targets
        all_targets = list(SAFE_DESTINATIONS)
        if shelter_data:
            for s in shelter_data:
                if s.get("lat") and s.get("lng"):
                    all_targets.append({
                        "name": s.get("name", "Shelter"),
                        "lat": s["lat"],
                        "lng": s["lng"],
                        "country": s.get("notes", ""),
                    })

        candidates = []
        for dest in all_targets:
            try:
                dest_hex = h3.latlng_to_cell(dest["lat"], dest["lng"], 6)
            except Exception:
                dest_hex = None
            if dest_hex in red_hexes:
                continue  # skip destinations in RED zones (active combat)
            d = _haversine(from_lat, from_lng, dest["lat"], dest["lng"])
            if d < 5:
                continue  # too close — already there
            if d > 500:
                continue  # too far — not a realistic drive
            candidates.append({**dest, "_dist": d})

        # Sort by distance, prefer closer destinations
        candidates.sort(key=lambda c: c["_dist"])

    if not candidates:
        return {
            "route_points": [],
            "distance_km": 0,
            "destination": "No safe destination found",
            "destination_country": "",
            "nearest_shelter": None,
            "narrative": "Unable to find a safe evacuation destination. All nearby cities are in danger zones.",
            "from": [from_lng, from_lat],
            "to": [from_lng, from_lat],
        }

    # ---- Try top 5 candidates, pick the route with fewest danger crossings ----
    best_route = None
    best_danger_count = float("inf")

    for dest in candidates[:5]:
        coords, dist_km, dur_min = _get_mapbox_route(from_lng, from_lat, dest["lng"], dest["lat"])
        if coords is None:
            continue

        danger_count, total_hexes, danger_ids = _score_route_safety(
            coords, hex_lookup, danger_hexes
        )

        if danger_count < best_danger_count:
            best_danger_count = danger_count
            best_route = {
                "route_points": coords,
                "distance_km": dist_km,
                "duration_min": int(dur_min),
                "destination": dest["name"],
                "destination_country": dest.get("country", ""),
                "danger_hexes_on_route": danger_ids,
                "from": [from_lng, from_lat],
                "to": [dest["lng"], dest["lat"]],
            }

        # Perfect route: zero danger crossings — no need to try more
        if danger_count == 0:
            break

    # ---- If best route crosses danger zones, try rerouting with offset waypoint ----
    if best_route and best_danger_count > 0:
        dest = None
        for c in candidates[:5]:
            if c["name"] == best_route["destination"]:
                dest = c
                break
        if dest:
            # Compute a perpendicular offset waypoint to steer the route around danger
            mid_lat = (from_lat + dest["lat"]) / 2
            mid_lng = (from_lng + dest["lng"]) / 2
            dlat = dest["lat"] - from_lat
            dlng = dest["lng"] - from_lng
            # Try both sides (perpendicular offsets)
            for sign in [1, -1]:
                offset_lat = mid_lat + sign * dlng * 0.15
                offset_lng = mid_lng - sign * dlat * 0.15
                alt_coords, alt_dist, alt_dur = _get_mapbox_route(
                    from_lng, from_lat, dest["lng"], dest["lat"],
                    waypoints=[[offset_lng, offset_lat]]
                )
                if alt_coords is None:
                    continue
                alt_danger, _, alt_danger_ids = _score_route_safety(
                    alt_coords, hex_lookup, danger_hexes
                )
                if alt_danger < best_danger_count:
                    best_danger_count = alt_danger
                    best_route = {
                        "route_points": alt_coords,
                        "distance_km": alt_dist,
                        "duration_min": int(alt_dur),
                        "destination": dest["name"],
                        "destination_country": dest.get("country", ""),
                        "danger_hexes_on_route": alt_danger_ids,
                        "from": [from_lng, from_lat],
                        "to": [dest["lng"], dest["lat"]],
                    }
                    if alt_danger == 0:
                        break

    if best_route is None:
        dest = candidates[0]
        return {
            "route_points": [[from_lng, from_lat], [dest["lng"], dest["lat"]]],
            "distance_km": round(_haversine(from_lat, from_lng, dest["lat"], dest["lng"]), 1),
            "duration_min": 0,
            "destination": dest["name"],
            "destination_country": dest.get("country", ""),
            "danger_hexes_on_route": [],
            "nearest_shelter": None,
            "narrative": "",
            "from": [from_lng, from_lat],
            "to": [dest["lng"], dest["lat"]],
        }

    # ---- Find nearest shelter near the DESTINATION (not start) ----
    nearest_shelter = None
    if shelter_data and best_route:
        dest_lat = best_route["to"][1]
        dest_lng = best_route["to"][0]
        best_shelter_dist = float("inf")
        for shelter in shelter_data:
            s_hex = None
            try:
                s_hex = h3.latlng_to_cell(shelter["lat"], shelter["lng"], 6)
            except Exception:
                pass
            if s_hex in red_hexes:
                continue
            d = _haversine(dest_lat, dest_lng, shelter["lat"], shelter["lng"])
            if d < best_shelter_dist:
                best_shelter_dist = d
                nearest_shelter = {**shelter, "distance_km": round(d, 1)}

    best_route["nearest_shelter"] = nearest_shelter
    best_route["narrative"] = ""  # Filled by Gemini in the endpoint
    return best_route


def generate_evac_narrative(route_result: dict, hex_lookup: dict) -> str:
    """
    Use Gemini to generate a human-readable evacuation recommendation.
    """
    from_coords = route_result["from"]
    to_coords = route_result["to"]
    dist = route_result.get("distance_km", 0)
    dur = route_result.get("duration_min", 0)
    destination = route_result.get("destination", "unknown")
    country = route_result.get("destination_country", "")
    danger_on_route = route_result.get("danger_hexes_on_route", [])
    shelter = route_result.get("nearest_shelter")

    shelter_info = ""
    if shelter:
        shelter_info = f"\nNearest safe facility en route: {shelter['name']} ({shelter.get('type', 'facility')}, {shelter.get('distance_km', '?')} km from start). Notes: {shelter.get('notes', '')}"

    danger_warning = ""
    if danger_on_route:
        danger_warning = f"\nWARNING: The route passes through {len(danger_on_route)} active danger zone(s). Consider waiting for an escort or traveling in a convoy."

    prompt = f"""You are a civilian safety advisor. A person is at {from_coords[1]:.4f}°N, {from_coords[0]:.4f}°E and needs to evacuate.

Route plan:
- Destination: {destination}, {country}
- Driving distance: {dist} km (approx {dur} min)
- Route follows actual roads via Mapbox Directions{danger_warning}{shelter_info}

Write 2-3 sentences of clear, actionable evacuation guidance:
1. Name the destination city and approximate drive time
2. If danger zones on route, warn to be cautious on that segment
3. Recommend traveling during daylight, bringing documents/water, and informing someone of your route

Be calm, direct, and specific. No bullet points. Address the person directly."""

    try:
        from alerting_agent import _get_client
        client = _get_client()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        print(f"  [evac] Gemini narrative failed: {e}")
        msg = f"Drive to {destination}"
        if country:
            msg += f", {country}"
        msg += f" ({dist} km, ~{dur} min)."
        if danger_on_route:
            msg += f" Caution: route crosses {len(danger_on_route)} active danger zone(s)."
        if shelter:
            msg += f" Nearest facility: {shelter['name']}."
        msg += " Travel during daylight. Bring ID, water, phone charger."
        return msg
