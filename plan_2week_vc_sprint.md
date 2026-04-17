# Sentinel — 2-Week VC Sprint Plan
**Deadline: ~April 7, 2026**
**Goal: Demonstrate all free resources are used, model is strong, business model is viable.**

---

## What VCs Want to See
1. You've exhausted free data sources (not just ACLED + GDELT + FIRMS + weather)
2. The model meaningfully improves with new data (onset detection, not just persistence)
3. Clear, defensible business model beyond "free for civilians"
4. Technical sophistication that justifies funding

## What Gets Deferred to Post-Funding
- Foundation model / spatial datacube / LSTM U-Net / Earthformer
- ACLED commercial license ($$$)
- Commercial satellite data (Planet, Maxar)
- Multi-theater expansion (Ukraine, Sudan, Ethiopia)
- EU AI Act full compliance
- Hire business co-founder

---

## Week 1: Data Integration Blitz (Days 1-7)

### Day 1-2: UCDP-GED Pipeline (ACLED Alternative)
- [ ] Download UCDP-GED v25.1 from ucdp.uu.se/downloads/
- [ ] Download UCDP Candidate Events (near-real-time)
- [ ] Write preprocessing: filter Levant bounding box, assign H3 hex-6, extract fatality estimates + actor info
- [ ] Compare UCDP events to ACLED events — overlap analysis
- [ ] Create `pipeline/01_preprocess_ucdp.py`
- **Why:** Removes ACLED licensing risk. CC BY 4.0. Shows VCs you have a legal ground truth.

### Day 2-3: VIIRS Nighttime Lights Pipeline
- [ ] Register NASA Earthdata account (free, instant)
- [ ] Install `blackmarblepy` (World Bank Python package)
- [ ] Download VNP46A2 daily nighttime lights for Levant bounding box
- [ ] Compute per-hex mean light intensity + 7-day delta + 30-day anomaly
- [ ] Create `pipeline/02_ingest_nightlights.py`
- **Why:** Strongest satellite conflict indicator. Light drops = destruction/displacement. Published research validates this.

### Day 3-4: IODA Internet Outage Integration
- [ ] Hit IODA API (ioda.inetintel.cc.gatech.edu) for Lebanon, Syria, Israel
- [ ] Extract sub-national connectivity scores (country + region + AS level)
- [ ] Compute connectivity_drop feature: current vs 7-day baseline
- [ ] Create `pipeline/03_ingest_ioda.py`
- **Why:** Internet shutdowns precede military action. Near-zero FPR. Real-time signal.

### Day 4-5: GDELT Feature Expansion
- [ ] Start extracting from GDELT GKG (not just events table):
  - GCAM emotional indicators (fear, anger, anxiety) filtered to Arabic-language Levant articles
  - Conflict-specific themes (CRISISLEX, TAX_FNCACT_REBEL, MILITARY)
  - Goldstein scale + tone per hex per day
- [ ] Deduplicate by URL/title similarity BEFORE feature extraction
- [ ] IDW interpolation with 20km distance cutoff
- [ ] Update `pipeline/04_ingest_gdelt.py` (or create v2)
- **Why:** You're using maybe 10% of GDELT's signal. GKG emotional indicators are highly predictive for onset.

### Day 5-6: Sentinel Hub / Copernicus Satellite Features
- [ ] Register at dataspace.copernicus.eu (free, instant)
- [ ] Use Statistical API to query Sentinel-2 NDVI per H3 hex for Levant
- [ ] Compute NDVI 7-day delta and 30-day anomaly per hex
- [ ] Create `pipeline/05_ingest_satellite.py`
- **Why:** Free satellite data from ESA. NDVI drops correlate with conflict (burned areas, destroyed agriculture). Shows VCs you're using space-based intelligence.

### Day 6-7: FEWS NET / Food Security + WorldPop
- [ ] Download IPC data for Lebanon from ipcinfo.org
- [ ] Map IPC phases to admin-1 regions, then to H3 hexes (area-weighted)
- [ ] Download WorldPop 100m gridded population for Levant
- [ ] Aggregate to H3 hex-6 (mean population per hex)
- [ ] Create `pipeline/06_ingest_food_security.py` and `pipeline/07_ingest_population.py`
- **Why:** Food insecurity is a proven conflict leading indicator. Population normalizes risk scores.

### Day 7: Feature Integration + Dataset Assembly
- [ ] Merge all new features into master training dataset:
  - UCDP-GED events (replacing/complementing ACLED)
  - Nightlight intensity + delta
  - Internet connectivity score + drop
  - GDELT GKG emotional indicators + deduped sentiment
  - Sentinel-2 NDVI + delta
  - IPC food security phase
  - Population density
- [ ] Create `pipeline/08_merge_features.py`
- [ ] Verify temporal alignment (all features use t-1 data, no leakage)
- [ ] Output: `data/processed/sentinel_v2_features.parquet`

---

## Week 2: Model + Business Demo (Days 8-14)

### Day 8-9: Dual-Model XGBoost Training (Onset + Continuation)
- [ ] Split training data into two subsets:
  - **Onset set:** `dangerous_roll14d == 0 AND ever_had_event_5yr == 1` (peaceful hexes that could plausibly see violence)
  - **Continuation set:** `dangerous_roll14d > 0` (hexes already experiencing violence)
- [ ] Train **xgb_onset** on onset set:
  - Use `scale_pos_weight` ≈ ratio of negatives to positives (~200)
  - Drop/de-emphasize lagged violence features (all zero by definition)
  - Emphasize: GDELT emotional indicators, IODA connectivity, FEWS NET, spatial lag from neighbors, nightlight trends
  - If `scale_pos_weight` insufficient, implement focal loss as custom XGBoost objective (~15 lines)
- [ ] Train **xgb_continuation** on continuation set:
  - Standard training (base rate is high enough)
  - Lagged violence, rolling averages, SAR damage, FIRMS density dominate here
- [ ] Temporal split for BOTH models: train 2020-01 to 2024-06, test 2024-07 to 2025-06
- [ ] Add onset-specific features:
  - Multi-ring spatial lags (ring-1/2/3 neighbor averages — "is violence approaching?")
  - De-escalation features (hours_since_last_event, violence_decay_rate)
  - Long-term memory (roll30d, months_since_last_conflict, relapse_count)
- [ ] Production scoring logic:
  - If hex `dangerous_roll14d == 0` → use xgb_onset score
  - If hex `dangerous_roll14d > 0` → use xgb_continuation score
- [ ] Evaluate SEPARATELY:
  - Onset AUC-PR (the key metric — show improvement over v1 baseline)
  - Continuation AUC-PR
  - Overall AUC-PR
- [ ] SHAP analysis on BOTH models — show that onset model uses fundamentally different features than continuation model
- **Why:** A single model drowns onset in continuation signal. Two models let each specialize. SHAP side-by-side proves to VCs you understand the hardest problem in the field. The onset model is where new data sources (GDELT GKG, IODA, FEWS NET) will show the biggest improvement.

### Day 10: Validation + Backtesting
- [ ] Walk-forward temporal validation (quarterly windows)
- [ ] Event-specific backtests: known escalations (Oct 7, 2023; Lebanon 2024 escalation; etc.)
- [ ] Score timelines showing Sentinel detected risk before events
- [ ] Generate visual: risk timeline overlaid with actual conflict events
- **Why:** Investors want to see "did it predict X?" Backtests answer this concretely.

### Day 11: Production Scoring Update
- [ ] Update `backend/05_score_live.py` to use v2 model + new features
- [ ] Wire new pipeline scripts into the APScheduler cron
- [ ] Verify live scoring works end-to-end with new data sources
- [ ] Fix critical bugs: CORS restriction, API key auth on mutation endpoints
- **Why:** The product needs to actually work with the new data, not just in a notebook.

### Day 12-13: Business Model Demo Prep
- [ ] Build a simple demo showing supply chain use case:
  - Map overlay of shipping routes (Red Sea, Suez, E. Mediterranean) on conflict hex map
  - Route risk scoring: "Route A through Red Sea = WARNING, Route B via Cape = CLEAR"
  - Example API response for a supply chain customer
- [ ] Prepare 1-page business model summary:
  - **Wedge 1:** Supply chain risk intelligence ($3-5B TAM, $50-250K/yr contracts)
  - **Wedge 2:** Insurance data provider ($1-4B TAM, parametric triggers)
  - **Wedge 3:** Alt data for finance ($1-2B TAM, trading signals)
  - Comparable exits: Recorded Future ($2.65B), Dataminr ($4.1B), Interos ($1B+)
- [ ] Prepare pitch metrics:
  - "Integrated 10+ free data sources (satellite, internet outages, food security, nightlights, GDELT NLP, UCDP events)"
  - "70x finer resolution than nearest competitor (H3 hex-6 vs PRIO-GRID)"
  - "Only 3 systems globally do ML-based conflict forecasting — we're one of them"
  - "Onset AUC-PR improved from X to Y with free data integration"
  - "Dual-model architecture: separate onset detector + continuation scorer — onset uses media sentiment, internet outages, food security; continuation uses historical violence patterns"

### Day 14: Polish + Buffer
- [ ] Run full pipeline end-to-end, verify no failures
- [ ] Generate model evaluation report (charts, metrics, feature importance)
- [ ] Update live dashboard with v2 model
- [ ] Prepare for VC demo

---

## Data Sources Summary: Before vs After

### Before (5 sources)
1. ACLED (needs commercial license!)
2. GDELT (basic event counts only)
3. NASA FIRMS (fire detections)
4. Open-Meteo (weather)
5. Mapbox (routing/tiles)

### After (13+ sources, all free)
1. **UCDP-GED** — conflict events (CC BY 4.0, replaces ACLED risk)
2. **GDELT GKG** — emotional indicators, deduped sentiment, Arabic-language analysis
3. **NASA FIRMS** — fire detections (existing)
4. **Open-Meteo** — weather (existing)
5. **VIIRS Black Marble** — nighttime lights (NASA, free)
6. **Sentinel-2** — NDVI vegetation change (ESA Copernicus, free)
7. **IODA** — internet outage detection (Georgia Tech, free)
8. **FEWS NET/IPC** — food security phases (free)
9. **WorldPop** — population density (free)
10. **Mapbox** — routing/tiles (existing)
11. **OONI** — internet censorship (stretch goal)
12. **OpenStreetMap** — infrastructure (stretch goal)
13. **Sentinel-1 SAR** — building damage detection (stretch goal)

---

## Success Criteria for VC Meeting
1. Model trained on UCDP-GED (no ACLED license risk)
2. 8+ new free data features integrated and contributing signal (SHAP proof)
3. **Dual-model architecture:** separate onset and continuation XGBoost models
4. Onset AUC-PR measurably improved over v1 baseline (v1 onset AUC-PR ~0.03-0.06)
5. SHAP side-by-side showing onset model uses different features than continuation model
6. Live dashboard running with v2 dual-model scoring
7. 1-page business model with TAM numbers and comparable exits
8. Supply chain demo showing route risk scoring
9. Event backtests showing Sentinel detected known escalations

---

## Stretch Goals (if time permits)
- [ ] Telegram channel monitoring (Telethon scraper for Lebanese news channels)
- [ ] Sentinel-1 SAR building damage detection (PWTT method)
- [ ] OONI censorship data integration
- [ ] IOM DTM displacement data
- [ ] VIEWS forecasts as ensemble input
- [ ] SPEI drought index
- [ ] Simple probability calibration (Platt scaling or isotonic regression)

---

## Key Risk
The biggest risk is trying to do too much in 2 weeks. The priority order is:
1. UCDP-GED (removes legal risk — do this first no matter what)
2. Nightlights + IODA (strongest new signals, easiest to integrate)
3. GDELT expansion (most signal per effort — you already have the pipeline)
4. Model retrain + validation (proves the new data helps)
5. Business model prep (tells the revenue story)

Everything else is bonus. Don't let perfect be the enemy of shipped.
