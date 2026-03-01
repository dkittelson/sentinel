# Sentinel -- Conflict Early Warning System

## Architecture Overview

Raw APIs -> Spatial Preprocessing -> ML Model -> AI Agent -> Final Output

- **Raw APIs:** ACLED (historical ground truth), GDELT 2.0 (live news sentiment), NASA FIRMS (thermal anomalies)
- **Spatial Preprocessing:** H3 hexagonal binning (resolution 6), rolling averages, velocity/delta features, spatial lag from neighbors
- **ML Model (XGBoost):** Outputs 0.0-1.0 escalation probability per hex per week -> Yellow / Orange / Red tier
- **AI Agent (LLM):** When hex crosses Red threshold (>0.7), drafts human-readable contextual alert from triggering features
- **App:** FastAPI backend + Mapbox hex overlay frontend + FCM push alerts by GPS

---

## Region
Lebanon + Northern Israel + Southern Syria (Levant corridor)
- Training data: 2020-01-01 to 2024-12-31
- ACLED rows after cleaning: ~73,900
- Hex-week training samples: 36,345 across 2,973 unique H3 hexes

---

## Current Model Performance
| Metric | Value |
|---|---|
| CV Mean ROC-AUC | 0.706 +/- 0.018 |
| Final Test ROC-AUC | 0.743 |
| Escalation Recall | 0.92 |
| Escalation Precision | 0.31 |
| Threshold | 0.40 (recall-biased, intentional) |
| Label | next_week_fatalities > 0 (will someone die here next week?) |

### Label Redesign (v2)
Changed primary label from "did event_count increase?" to "next_week_fatalities > 0".
Old label was noisy (1→2 events counted as escalation) and not civilian-relevant.
New label asks the direct question: will someone die in this hex next week?
Result: recall improved 0.86→0.92 at cost of precision 0.37→0.31 and AUC 0.764→0.743.
This tradeoff is correct for a civilian warning system -- missing fatal weeks is worse than false alarms.
Old label kept as `label_trend` in acled_h3.csv for reference.

### Precision Ceiling -- Confirmed
Ran 20+ experiments across: stricter labels, z-score features, interaction terms,
log transforms, seasonal features, Random Forest, calibrated XGB, alternate label
definitions, hyperparameter sweeps. NONE beat both precision AND recall vs baseline
simultaneously. This is the Bayes error limit on open-source OSINT data -- confirmed.
Precision will improve at inference time when GDELT/FIRMS provide live (not lagged) signal.

### Architecture: Two-Layer Alerting
- **Strategic layer** (XGBoost weekly): "Is this hex trending toward escalation?" → 0.0-1.0 score
- **Tactical layer** (rule-based immediate, backend/tactical_alert.py): "Is this hex dangerous RIGHT NOW?"
  Uses live FIRMS + GDELT thresholds; no ML needed; CLEAR/WATCH/WARNING/DANGER tiers
  Triggers FCM push when tactical score ≥ 0.75 (DANGER tier)

### New Features (v2, 32 total)
Added actor novelty features to BASE_FEATURES:
- actor_pair_count -- unique (actor1, actor2) pairs active in hex-week
- actor_pair_delta -- week-over-week change in actor pairs (new actors entering conflict)
- actor_pair_velocity -- actor_pair_count / 4w rolling baseline (novelty momentum)

---

## Feature Set (28 features)

### Base / ACLED (18)
- event_count, total_fatalities, max_fatalities
- battle_count, explosion_count, vac_count
- population_best, unique_actors
- event_count_roll2w, fatalities_roll2w, event_count_roll4w, fatalities_roll4w
- event_count_delta, fatality_delta (week-over-week velocity)
- event_velocity, fatality_velocity (ratio vs 4w baseline)
- neighbor_event_avg, neighbor_fatal_sum (H3 ring-1 spatial lag)

### GDELT (6)
- gdelt_event_count, gdelt_avg_tone, gdelt_min_goldstein
- gdelt_avg_goldstein, gdelt_num_articles, gdelt_hostility

### NASA FIRMS (4)
- firms_hotspot_count, firms_avg_frp, firms_max_frp, firms_spike

---

## Pipeline Files
| File | Purpose | Status |
|---|---|---|
| backend/pipeline/01_preprocess_acled.py | H3 binning, rolling/velocity/spatial features, labels | done |
| backend/pipeline/02_train_model.py | XGBoost training, CV, eval report, feature importance | done |
| backend/pipeline/03_ingest_gdelt.py | GDELT weekly download + hex aggregation | done |
| backend/pipeline/04_ingest_firms.py | NASA FIRMS SP archive download + hex aggregation | done |
| data/processed/acled_h3_gdelt_firms.csv | Final enriched training/inference feature table | done |
| models/xgb_sentinel.ubj | Trained XGBoost model | done |
| models/eval_report.txt | CV + test set evaluation report | done |
| models/feature_importance.png | Feature importance bar chart | done |

---

## Master Checklist

### Phase 1 -- Data and ML Pipeline
- [x] Register ACLED account + download Levant dataset (2020-2024)
- [x] Set up Python venv + install dependencies (pandas, xgboost, h3, scikit-learn, etc.)
- [x] Build 01_preprocess_acled.py -- H3 binning, rolling features, escalation labels
- [x] Add velocity/momentum features (event_count_delta, event_velocity, fatality_delta, fatality_velocity)
- [x] Add spatial lag features (neighbor_event_avg, neighbor_fatal_sum via H3 ring-1)
- [x] Build 02_train_model.py -- XGBoost with TimeSeriesSplit CV, scale_pos_weight, eval report
- [x] Train and evaluate baseline model (ROC-AUC 0.764, recall 0.86)
- [x] Get NASA FIRMS MAP_KEY (earthdata.nasa.gov)
- [x] Build 03_ingest_gdelt.py -- pull news sentiment scores per hex-week for Levant
- [x] Build 04_ingest_firms.py -- pull NASA FIRMS SP archive thermal anomalies per hex-week
- [x] Merge GDELT + FIRMS features into training data and retrain
- [x] Run 23 precision improvement experiments -- confirmed Bayes error ceiling, shipped baseline
- [x] Redesign label: next_week_fatalities > 0 (more direct civilian danger signal, recall 0.86→0.92)
- [x] Add actor novelty features: actor_pair_count, actor_pair_delta, actor_pair_velocity
- [x] Build backend/tactical_alert.py -- rule-based immediate danger layer (CLEAR/WATCH/WARNING/DANGER)
- [x] Retrain final model with all features + new label (ROC-AUC 0.743, recall 0.92)

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
- Training label: did event_count increase next week? (binary escalation, not severity)
- Threshold 0.40 -- recall-biased by design; over-warning is better than missing events
- Supabase over Firebase -- need PostGIS spatial queries; Supabase gives managed Postgres + REST for free
- Web frontend, not React Native -- same Mapbox demo, no app store friction
- GDELT source: daily CSV download (no API key needed), weekly sampling
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
