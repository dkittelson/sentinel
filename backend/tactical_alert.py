"""
Tactical Alert Layer — Rule-Based Immediate Danger Scoring
============================================================
This is SEPARATE from the weekly XGBoost model (strategic layer).

The strategic model answers: "Is this hex trending toward escalation this week?"
This module answers:         "Is this hex in active/imminent danger RIGHT NOW?"

It uses live GDELT + FIRMS signals with hard thresholds — no ML needed.
The advantage: immediate response to new signals without waiting for weekly retrain.

Called by FastAPI when serving /hex/{h3_id} and when evaluating push alerts.

Outputs a TacticalAlert with:
  - risk_level: "CLEAR" / "WATCH" / "WARNING" / "DANGER"
  - score: 0.0–1.0
  - triggers: list of human-readable strings explaining what fired
  - should_alert: bool (True = send FCM push to users in this hex)
"""

from dataclasses import dataclass, field
from typing import List, Optional
import pandas as pd
import numpy as np


@dataclass
class TacticalAlert:
    h3_id: str
    risk_level: str          # CLEAR / WATCH / WARNING / DANGER
    score: float             # 0.0–1.0
    triggers: List[str]      # human-readable reasons
    should_alert: bool       # True = send FCM push notification
    strategic_score: Optional[float] = None   # XGBoost weekly probability
    strategic_tier: Optional[str] = None      # Yellow / Orange / Red


# ── Thresholds (tunable) ──────────────────────────────────────────────────────
# Each trigger contributes a weight to the total score.
# Score >= 0.4 → WATCH, >= 0.6 → WARNING, >= 0.8 → DANGER + FCM push.

FIRMS_HOTSPOT_THRESHOLD   = 2      # >= N thermal detections in hex this period
FIRMS_FRP_THRESHOLD       = 50.0   # MW — high FRP = large/intense fire/explosion
FIRMS_SPIKE_WEIGHT        = 0.35   # firms_spike flag contribution

GDELT_HOSTILITY_THRESHOLD = 0.55   # 0–1 scale, 0.55 is significantly hostile
GDELT_GOLDSTEIN_THRESHOLD = -5.0   # below -5 = strongly destabilizing events
GDELT_HOSTILITY_WEIGHT    = 0.25
GDELT_GOLDSTEIN_WEIGHT    = 0.20

NEIGHBOR_PRESSURE_THRESHOLD = 3.0  # avg events in ring-1 neighbors
NEIGHBOR_PRESSURE_WEIGHT    = 0.15

VELOCITY_THRESHOLD   = 2.0   # event count > 2x the 4-week rolling average
VELOCITY_WEIGHT      = 0.20

STRATEGIC_RED_WEIGHT      = 0.15   # adds weight if XGBoost already flagged Red

# Tier thresholds
WATCH_THRESHOLD   = 0.35
WARNING_THRESHOLD = 0.55
DANGER_THRESHOLD  = 0.75
ALERT_THRESHOLD   = 0.75   # FCM push fires at this score


def score_hex(
    h3_id: str,
    # FIRMS features (current period)
    firms_hotspot_count: float = 0,
    firms_avg_frp: float = 0,
    firms_max_frp: float = 0,
    firms_spike: int = 0,
    # GDELT features (current week)
    gdelt_hostility: float = 0,
    gdelt_min_goldstein: float = 0,
    gdelt_avg_tone: float = 0,
    gdelt_event_count: float = 0,
    # ACLED-derived features (from latest scored week)
    event_velocity: float = 1.0,
    neighbor_event_avg: float = 0,
    neighbor_fatal_sum: float = 0,
    # Strategic model output
    strategic_score: float = 0.0,
) -> TacticalAlert:
    """
    Score a single hex for immediate/tactical danger level.
    All inputs are scalar values for the current time window.
    """

    score = 0.0
    triggers = []

    # ── FIRMS: thermal anomaly signals ────────────────────────────────────────
    if firms_spike:
        score += FIRMS_SPIKE_WEIGHT
        triggers.append(
            f"Thermal spike detected ({firms_hotspot_count:.0f} hotspots, "
            f"max FRP={firms_max_frp:.0f} MW)"
        )
    elif firms_hotspot_count >= FIRMS_HOTSPOT_THRESHOLD:
        partial = min(firms_hotspot_count / 5.0, 1.0) * FIRMS_SPIKE_WEIGHT * 0.6
        score += partial
        triggers.append(
            f"Elevated thermal activity ({firms_hotspot_count:.0f} hotspots)"
        )

    if firms_max_frp >= FIRMS_FRP_THRESHOLD:
        score += 0.10
        triggers.append(f"High-intensity heat source (FRP={firms_max_frp:.0f} MW)")

    # ── GDELT: news sentiment signals ─────────────────────────────────────────
    if gdelt_hostility >= GDELT_HOSTILITY_THRESHOLD:
        weight = GDELT_HOSTILITY_WEIGHT * min(gdelt_hostility / 0.8, 1.0)
        score += weight
        triggers.append(
            f"Hostile media coverage (hostility={gdelt_hostility:.2f}, "
            f"tone={gdelt_avg_tone:.1f})"
        )

    if gdelt_min_goldstein <= GDELT_GOLDSTEIN_THRESHOLD:
        weight = GDELT_GOLDSTEIN_WEIGHT * min(
            abs(gdelt_min_goldstein) / 10.0, 1.0
        )
        score += weight
        triggers.append(
            f"Destabilizing events in news "
            f"(Goldstein={gdelt_min_goldstein:.1f})"
        )

    # ── Neighbor pressure ─────────────────────────────────────────────────────
    if neighbor_event_avg >= NEIGHBOR_PRESSURE_THRESHOLD:
        weight = NEIGHBOR_PRESSURE_WEIGHT * min(neighbor_event_avg / 8.0, 1.0)
        score += weight
        triggers.append(
            f"High surrounding activity "
            f"({neighbor_event_avg:.1f} avg events in adjacent hexes)"
        )

    # ── Velocity / momentum ───────────────────────────────────────────────────
    if event_velocity >= VELOCITY_THRESHOLD:
        weight = VELOCITY_WEIGHT * min(event_velocity / 4.0, 1.0)
        score += weight
        triggers.append(
            f"Event rate spiking ({event_velocity:.1f}x above 4-week baseline)"
        )

    # ── Strategic model boost ─────────────────────────────────────────────────
    strategic_tier = None
    if strategic_score >= 0.7:
        score += STRATEGIC_RED_WEIGHT
        strategic_tier = "Red"
        triggers.append(
            f"ML model flagged Red (escalation probability={strategic_score:.2f})"
        )
    elif strategic_score >= 0.5:
        score += STRATEGIC_RED_WEIGHT * 0.5
        strategic_tier = "Orange"
    elif strategic_score >= 0.3:
        strategic_tier = "Yellow"

    # ── Clamp + tier ─────────────────────────────────────────────────────────
    score = min(score, 1.0)

    if score >= DANGER_THRESHOLD:
        risk_level = "DANGER"
    elif score >= WARNING_THRESHOLD:
        risk_level = "WARNING"
    elif score >= WATCH_THRESHOLD:
        risk_level = "WATCH"
    else:
        risk_level = "CLEAR"

    return TacticalAlert(
        h3_id=h3_id,
        risk_level=risk_level,
        score=round(score, 3),
        triggers=triggers if triggers else ["No significant signals detected"],
        should_alert=(score >= ALERT_THRESHOLD),
        strategic_score=strategic_score,
        strategic_tier=strategic_tier,
    )


# ── Batch scoring ─────────────────────────────────────────────────────────────
def score_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Score a full hex-week DataFrame. expects columns matching the feature names above.
    Returns original df with tactical_score, tactical_tier, should_alert columns added.
    """
    records = []
    for _, row in df.iterrows():
        alert = score_hex(
            h3_id=row.get("h3_id", ""),
            firms_hotspot_count=row.get("firms_hotspot_count", 0),
            firms_avg_frp=row.get("firms_avg_frp", 0),
            firms_max_frp=row.get("firms_max_frp", 0),
            firms_spike=row.get("firms_spike", 0),
            gdelt_hostility=row.get("gdelt_hostility", 0),
            gdelt_min_goldstein=row.get("gdelt_min_goldstein", 0),
            gdelt_avg_tone=row.get("gdelt_avg_tone", 0),
            gdelt_event_count=row.get("gdelt_event_count", 0),
            event_velocity=row.get("event_velocity", 1.0),
            neighbor_event_avg=row.get("neighbor_event_avg", 0),
            neighbor_fatal_sum=row.get("neighbor_fatal_sum", 0),
            strategic_score=row.get("ml_score", 0.0),
        )
        records.append({
            "tactical_score": alert.score,
            "tactical_tier": alert.risk_level,
            "should_alert": alert.should_alert,
            "tactical_triggers": " | ".join(alert.triggers),
        })

    result_df = pd.DataFrame(records, index=df.index)
    return pd.concat([df, result_df], axis=1)


# ── Quick self-test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Tactical Alert Layer — Self Test\n")

    # Quiet hex — nothing happening
    a = score_hex("hex_quiet", firms_hotspot_count=0, gdelt_hostility=0.1,
                  event_velocity=0.8, strategic_score=0.15)
    print(f"Quiet hex:     {a.risk_level:8s}  score={a.score:.2f}  alert={a.should_alert}")
    print(f"  Triggers: {a.triggers}\n")

    # Heating up — news hostility + velocity
    b = score_hex("hex_watch", gdelt_hostility=0.60, event_velocity=2.5,
                  neighbor_event_avg=4.0, strategic_score=0.45)
    print(f"Heating up:    {b.risk_level:8s}  score={b.score:.2f}  alert={b.should_alert}")
    print(f"  Triggers: {b.triggers}\n")

    # Active danger — thermal spike + hostile news + model flagged Red
    c = score_hex("hex_danger", firms_hotspot_count=5, firms_max_frp=80,
                  firms_spike=1, gdelt_hostility=0.75, gdelt_min_goldstein=-7.5,
                  event_velocity=3.5, neighbor_event_avg=6.0, strategic_score=0.82)
    print(f"Active danger: {c.risk_level:8s}  score={c.score:.2f}  alert={c.should_alert}")
    print(f"  Triggers: {c.triggers}\n")

    print("Self-test passed.")
