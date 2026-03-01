# Sentinel -- Conflict Early Warning System

## Architecture Overview

Raw APIs -> Spatial Preprocessing -> ML Model -> AI Agent -> Final Output

- **Raw APIs:** ACLED (historical ground truth), GDELT 1.0 (live news sentiment), NASA FIRMS (thermal anomalies)
- **Spatial Preprocessing:** H3 hexagonal binning (resolution 6), daily grain, rolling 3d/7d/14d features, velocity/delta features, spatial lag from ring-1 neighbors
- **ML Model (XGBoost):** Outputs 0.0-1.0 danger probability per hex per day → Yellow / Orange / Red tier
- **AI Agent (LLM):** When hex crosses Red threshold (>0.7), drafts human-readable contextual alert from triggering features
- **App:** FastAPI backend + Mapbox hex overlay frontend + FCM push alerts by GPS

---

## Region
Lebanon + Northern Israel + Southern Syria (Levant corridor)
- Training data: 2020-01-01 to 2024-12-10
- ACLED rows after cleaning: ~81,258 (includes riots, protests, all dangerous event types)
- Hex-day training samples: 8,551,410 across 4,735 unique H3 hexes

---

### Current Model Performance
| Metric | Value |
|---|---|
| CV Mean ROC-AUC | 0.770 +/- 0.029 |
| Final Test ROC-AUC (Standard) | 0.815 |
| Final Test AUC-PR (Standard) | 0.309 |
| Final Test ROC-AUC (Focal) | 0.816 |
| Final Test AUC-PR (Focal) | 0.317 |
| Best F1 (Standard @ 0.90) | 0.358 (P=0.356, R=0.360) |
| Best F1 (Focal @ 0.30) | 0.360 (P=0.448, R=0.301) |

### Alert Tier Thresholds (Focal Loss model)
| Tier | Threshold | Precision | Recall | Alerts/day |
|---|---|---|---|---|
| Yellow | 0.15 | 0.101 | 0.614 | ~517 |
| Orange | 0.20 | 0.181 | 0.513 | ~241 |
| Red | 0.30 | 0.448 | 0.301 | ~57 |

Production model: `models/xgb_focal.ubj` (focal loss, gamma=2, alpha=0.25)
Backup model: `models/xgb_standard.ubj`

### Label (v4 -- Daily 72h)
Label: `next_72h_dangerous > 0` -- will ANY dangerous event occur in this hex in the next 72 hours?

"Dangerous" = anything threatening to an ordinary civilian:
- Battles (armed clashes, territorial takeovers)
- Explosions/Remote violence (airstrikes, shelling, IEDs, drones)
- Violence against civilians (attacks, abductions, sexual violence, suicide bombs)
- Riots (mob violence, looting, violent demonstrations)
- Violent protest sub-types (excessive force against protesters, protest with intervention)

Excludes: Strategic developments (non-violent admin), peaceful protests.
Label balance: 1.5% positive (130K dangerous hex-days out of 8.5M)
XGBoost handles this with scale_pos_weight=64.51.

### Architecture: Two-Layer Alerting
- **Strategic layer** (XGBoost daily): "Will something dangerous happen in this hex in the next 48h?" → 0.0-1.0 score
- **Tactical layer** (rule-based immediate, backend/tactical_alert.py): "Is this hex dangerous RIGHT NOW?"
  Uses live FIRMS + GDELT thresholds; no ML needed; CLEAR/WATCH/WARNING/DANGER tiers
  Triggers FCM push when tactical score ≥ 0.75 (DANGER tier)

---

## Feature Set (44 features, daily grain)

### Base / ACLED (34)
- event_count, dangerous_count, total_fatalities, max_fatalities
- battle_count, explosion_count, vac_count, riot_count
- population_best, unique_actors
- dangerous_roll3d, dangerous_roll7d, dangerous_roll14d (rolling danger averages)
- fatalities_roll3d, fatalities_roll7d, fatalities_roll14d
- event_roll3d, event_roll7d, event_roll14d
- dangerous_delta, fatality_delta (day-over-day velocity)
- dangerous_velocity, fatality_velocity (ratio vs 14d baseline)
- neighbor_danger_avg, neighbor_fatal_sum (H3 ring-1 spatial lag)
- actor_pair_count, actor_pair_delta, actor_pair_velocity (novelty features)
- **dangerous_lag1, dangerous_lag2** (yesterday / 2-days-ago dangerous events)
- **fatalities_lag1, battle_lag1, explosion_lag1** (type-specific yesterday lags)

### GDELT (7)
- gdelt_event_count, gdelt_avg_tone, gdelt_min_goldstein
- gdelt_avg_goldstein, gdelt_num_articles, gdelt_hostility
- neighbor_gdelt_hostility_avg (spatial lag)

### NASA FIRMS (5)
- firms_hotspot_count, firms_avg_frp, firms_max_frp, firms_spike
- neighbor_firms_spike_sum (spatial lag)

---

## Pipeline Files
| File | Purpose | Status |
|---|---|---|
| backend/pipeline/01_preprocess_acled.py | H3 binning, daily rolling/velocity/spatial features, 48h labels | done |
| backend/pipeline/02_train_model.py | XGBoost training, CV, eval report, feature importance | done |
| backend/pipeline/03_ingest_gdelt.py | GDELT daily download + hex-day aggregation | done |
| backend/pipeline/04_ingest_firms.py | NASA FIRMS SP archive download + hex-day aggregation | done |
| data/processed/acled_h3.csv | ACLED hex-day panel (8.5M rows, 32 cols, label=1.1%) | done |
| data/processed/acled_h3_gdelt.csv | ACLED+GDELT merged hex-day table | done |
| data/processed/acled_h3_gdelt_firms.csv | Final enriched training/inference feature table | done |
| models/xgb_sentinel.ubj | Production model (focal loss) | done (AUC-PR 0.317, F1 0.360) |
| models/xgb_standard.ubj | Standard XGBoost backup | done (AUC-PR 0.309, F1 0.358) |
| models/eval_report.txt | CV + test set evaluation report | done |
| models/feature_importance.png | Feature importance bar chart | done |

---

## Master Checklist

### Phase 1 -- Data and ML Pipeline
- [x] Register ACLED account + download Levant dataset (2020-2024)
- [x] Set up Python venv + install dependencies (pandas, xgboost, h3, scikit-learn, etc.)
- [x] Build 01_preprocess_acled.py -- H3 binning, rolling features, escalation labels
- [x] Add velocity/momentum features (dangerous_delta, dangerous_velocity, fatality_delta, fatality_velocity)
- [x] Add spatial lag features (neighbor_danger_avg, neighbor_fatal_sum via H3 ring-1, vectorized)
- [x] Build 02_train_model.py -- XGBoost with TimeSeriesSplit CV, scale_pos_weight, eval report
- [x] Train and evaluate baseline model (ROC-AUC 0.764, recall 0.86)
- [x] Get NASA FIRMS MAP_KEY (earthdata.nasa.gov)
- [x] Build 03_ingest_gdelt.py -- pull news sentiment scores per hex-day for Levant
- [x] Build 04_ingest_firms.py -- pull NASA FIRMS SP archive thermal anomalies per hex-day
- [x] Merge GDELT + FIRMS features into training data and retrain
- [x] Run 23 precision improvement experiments -- confirmed Bayes error ceiling, shipped baseline
- [x] Redesign label: next_week_fatalities > 0 (more direct civilian danger signal, recall 0.86→0.92)
- [x] Add actor novelty features: actor_pair_count, actor_pair_delta, actor_pair_velocity
- [x] Build backend/tactical_alert.py -- rule-based immediate danger layer (CLEAR/WATCH/WARNING/DANGER)
- [x] Retrain final model with all features + new label (ROC-AUC 0.743, recall 0.92)
- [x] Redesign preprocessing to daily grain + 48h lookahead label (hex-day, 8.5M rows, label=1.1%)
- [x] Expand "dangerous" definition: Battles + Explosions + VAC + Riots + violent protest sub-types
- [x] Rebuild GDELT ingestion to daily grain (1,826 daily downloads, aggregate per hex-day)
- [x] Rebuild FIRMS ingestion to daily grain (5-day chunks, aggregate per hex-day via acq_date)
- [x] Re-run GDELT ingestion (running in background) -- acled_h3_gdelt.csv
- [x] Re-run FIRMS ingestion (after GDELT) -- acled_h3_gdelt_firms.csv
- [x] Retrain model with new daily-grain features and 48h label (AUC 0.835, recall 0.75)
- [x] Add temporal lag features (dangerous_lag1/2, fatalities_lag1, battle_lag1, explosion_lag1)
- [x] Retrain with lag features + all M4 cores (tree_method=hist, nthread=-1) -- AUC-PR 0.329
- [x] Change label to 72h lookahead (base rate 1.1% -> 1.5%, inline relabeling in 02_train_model.py)
- [x] Add focal loss custom objective (gamma=2, alpha=0.25) -- best F1 0.360, precision 0.448 @ threshold 0.30
- [x] Fine-grained threshold sweep (0.05 steps) on both models -- set tier thresholds Yellow/Orange/Red

### Phase 2 -- Backend
- [ ] Set up Supabase project (managed Postgres + PostGIS, free tier)
- [ ] Design DB schema: hex_grid, risk_scores, acled_events, gdelt_signals, firms_anomalies
- [ ] Build main.py FastAPI server
  - [ ] GET /hexes -- returns all hex IDs + current risk score + tier
  - [ ] GET /hex/{h3_id} -- returns full feature breakdown for one hex
  - [ ] GET /hexes/region?lat=&lon=&radius_km= -- spatial query around GPS point
  - [ ] POST /ingest/run -- manually trigger full pipeline refresh
- [ ] Build cron job scheduler (APScheduler) to pull GDELT + FIRMS every 15 min
- [ ] Build 05_score_live.py -- loads saved XGBoost model, runs inference on latest hex features, writes scores to DB
- [ ] Add .env support for all API keys (ACLED, FIRMS MAP_KEY, Supabase URL/key)

### Phase 3 -- AI Alerting Agent
- [ ] Choose LLM (OpenAI GPT-4o or Claude claude-sonnet-4-5 via API)
- [ ] Build alerting_agent.py -- reads top triggering features for a Red hex, constructs prompt, returns alert text
- [ ] Prompt includes: hex location name, event types, fatality delta, neighbor pressure, GDELT sentiment, FIRMS spike
- [ ] Integrate with FastAPI: when a hex flips to Red, auto-call agent and store alert text in DB

### Phase 4 -- Frontend
- [ ] Set up React web app (recommended over React Native for hackathon speed)
- [ ] Set up Mapbox GL JS with dark mode base map
- [ ] Render H3 hex grid as GeoJSON polygon layer, colored by risk tier (Yellow / Orange / Red)
- [ ] Fetch hex data from FastAPI /hexes endpoint on interval
- [ ] Click on hex -> show feature breakdown sidebar (event count, fatalities, GDELT sentiment, FIRMS spike, AI alert text)
- [ ] Auto-center map on user GPS location (browser Geolocation API)

### Phase 5 -- Alerting
- [ ] Set up Firebase project + FCM
- [ ] Backend: when hex flips to Red, send FCM push to users whose GPS is within that hex or ring-1 neighbors
- [ ] Frontend: register FCM token and handle push notification display

### Phase 6 -- Demo Prep
- [ ] Backtest demo: render map Oct 2023 (pre-escalation) -> Nov 2023, show model predicting the ramp
- [ ] Prepare precision/recall curve + AUC score slide for judges
- [ ] Satellite CV layer listed as Phase 2 roadmap item only -- do NOT build for hackathon

---

## Key Design Decisions (Locked)
- H3 resolution 6 (~36km2 hexes) -- coarse enough to aggregate signal, fine enough for civilian relevance
- Training grain: daily (hex-day), NOT weekly -- enables 48h lookahead predictions for live app
- Training label: next_48h_dangerous > 0 -- will any dangerous event (battle/explosion/riot/VAC/violent protest) occur in this hex in the next 48h?
- "Dangerous" excludes: Strategic developments (non-violent admin), peaceful protests
- **Threshold 0.40** -- recall-biased by design; over-warning is better than missing events
- **Alert tiers (focal model)**: Yellow ≥ 0.15 (R=0.614), Orange ≥ 0.20 (R=0.513), Red ≥ 0.30 (P=0.448)
- Supabase over Firebase -- need PostGIS spatial queries; Supabase gives managed Postgres + REST for free
- Web frontend, not React Native -- same Mapbox demo, no app store friction
- GDELT source: daily CSV download (no API key needed), one file per day
- FIRMS source: VIIRS_SNPP_SP (Standard Processing archive) -- covers full 2020-2024 range
  NRT source only holds ~2 months; SP goes back to 2012

---

## API Keys Needed
| Service | Key Type | Status |
|---|---|---|
| ACLED | Free API key (email registration) | done |
| NASA FIRMS | Free MAP_KEY (earthdata.nasa.gov) | done -- in .env |
| GDELT | No key required | free |
| Supabase | Project URL + anon key | set up with backend |
| Mapbox | Public token | set up with frontend |
| OpenAI / Anthropic | API key | set up with alerting agent |
