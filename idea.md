# Sentinel — Conflict Risk Intelligence

## Problem
Civilians in conflict zones have no access to the intelligence that governments and militaries rely on. When violence escalates, they learn from word of mouth or breaking news — after the window to act has closed. The data exists but is scattered across dozens of sources and accessible only to researchers.

## Solution
Sentinel fuses 74 data sources across 6 domains into a living danger map answering: *Will something dangerous happen in my area in the next 72 hours?* When risk spikes, it suggests evacuation routes avoiding danger zones, identifies shelters, and delivers plain-language briefings — framed as decision support, never commands.

## Products
1. **Sentinel API** — hex-level risk scores (72h/7d/30d), batch + real-time. For supply chain, insurers, corporates, NGOs.
2. **Sentinel Dashboard** — web interface for institutional users (aid workers, journalists, security teams).
3. **Sentinel Alerts** — free consumer Telegram bot + mobile app for civilians. The mission.

## Tech Stack
| Layer | Stack |
|---|---|
| Data (74 sources) | UCDP-GED (primary), GDELT GKG (2,230 emotional dims), VIIRS NTL, NASA FIRMS, IODA, Cloudflare Radar, FEWS NET/IPC, WFP food prices, Pikud HaOref, Sentinel-2 NDVI, Telegram OSINT, Google Trends, UNIFIL, WorldPop, LBP exchange rate, religious calendar + 54 more (see `research/complete_data_portfolio.md`) |
| Spatial | H3 hex grid (res 6, ~36km²), daily grain, rolling/velocity/spatial-lag features |
| ML | Dual-model XGBoost v2 (onset + continuation) → spatial foundation model (post-funding, 5-10M params) |
| Backend | FastAPI, Supabase (Postgres + PostGIS), APScheduler 15min cron |
| AI agent | Gemini 2.5 Flash with Google Search grounding |
| Frontend | Vite + React, Mapbox GL JS, h3-js. Mobile-first, EN/AR i18n |
| Alerts | Two-layer: strategic ML scores (daily) + tactical rule-based triggers (real-time) |

## ML Architecture
**Current (v2 — 2-week sprint):**
Dual-model XGBoost. ~120-150 features from 20 sources.
- **Onset model:** Predicts violence arriving in peaceful areas. Trained on GDELT GKG emotional indicators, IODA internet outages, food prices, currency data, Google Trends mobilization signals, spatial lag from neighbors, nightlight trends, calendar features. Uses `scale_pos_weight` or focal loss for extreme class imbalance (~0.05% positive rate).
- **Continuation model:** Predicts escalation in active conflict areas. Trained on lagged violence, rolling counts, FIRMS fire density, nightlight acute drops.
- **Scoring logic:** peaceful hex → onset model; active hex → continuation model.

**Target (post-funding):**
Two-branch architecture with domain-specific foundation model.
- **Branch A — Spatial model** (5-10M params, head-to-head: LSTM U-Net vs Earthformer). 5-channel datacube × 64×64 tiles × 14 days.
- **Branch B — Enhanced onset detector** with XLM-R text embeddings + full Tier 2/3 features.
- **Meta-learner → Venn-ABERS → BCCP calibration** → score + confidence interval + attribution.
- **Ground truth: UCDP-GED (CC BY 4.0).** ACLED pending commercial license.
- **Primary evaluation metric: Onset AUC-PR** — not overall AUC (dominated by continuation).

## Revenue
Three wedges: Supply Chain Risk Intelligence ($3-5B TAM), Insurance/Parametric Triggers ($1-4B TAM), Alternative Data for Finance ($1-2B TAM). See `research/business_model_analysis.md`.

## Competitive Position
- Only 3 systems globally do ML-based conflict forecasting (Sentinel, ViEWS, ACLED CAST)
- 70x finer resolution than nearest competitor (H3 hex-6 vs PRIO-GRID)
- Only system targeting civilians as primary users
- Comparable exits: Recorded Future ($2.65B), Dataminr ($4.1B), Interos ($1B+)

## Target Audience
**Primary — Civilians:** Danger map, push notifications, evacuation routing. EN/AR. Zero training required.
**Secondary — Institutions:** Dashboard, API, area briefings. Supply chain + insurance + finance are the revenue markets.
**Positioning:** Consumer-grade civilian safety intelligence. Moat = predicted spatial risk + evacuation routing + human feedback loop.
**First deployment:** Levant. Expands via region config files to Ukraine, Sudan, Ethiopia, then further.
