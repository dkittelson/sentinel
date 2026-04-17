# Sentinel ML Pipeline — Master Checklist

## Working Style
The user is learning Python, ML, and data engineering. Claude should **teach and guide**, not write code directly. Explain concepts, suggest approaches, point out pitfalls, and let the user write the code themselves. When reviewing their code, explain *why* something should change, not just *what* to change.

## Data Portfolio
**76 data sources** across 7 domains (text/NLP, satellite, connectivity, socioeconomic, military/OSINT, calendar/context, maritime/supply chain). See `research/complete_data_portfolio.md` for the full inventory.

| Tier | Sources | Features | Timeline |
|------|---------|----------|----------|
| Current (v1) | 5 | ~52 | Live |
| Sprint v2 (Tier 1) | 22 | ~120-150 + maritime overlays | 2-week VC sprint |
| Post-funding (Tier 2) | 49 | ~200-250 | Month 2-3 |
| Full portfolio (Tier 3) | 76 | ~300+ | Quarter 2+ |

**New in Tier 1:** IMF PortWatch (2,033 ports + 28 chokepoints, free API) and aisstream.io (coastal AIS, free). These are context overlays for supply chain/insurance APIs, not model inputs.

## Model Architecture
**Dual-model XGBoost** — two separate models, not one:
- **Onset model:** Trained on peaceful hex-days (`dangerous_roll14d == 0 AND ever_had_event_5yr == 1`). Uses GDELT GKG emotions, IODA, food prices, LBP rate, Google Trends, spatial lag, nightlights, calendar. `scale_pos_weight` or focal loss for extreme class imbalance.
- **Continuation model:** Trained on active-conflict hex-days (`dangerous_roll14d > 0`). Uses lagged violence, rolling counts, FIRMS, nightlight acute drops, SAR damage.
- **Scoring:** If hex is peaceful → onset model. If hex is active → continuation model.
- **Post-funding:** Meta-learner combining onset + continuation + spatial model. Venn-ABERS + BCCP calibration.

## Phase 0: VC Sprint — Urgent (2 weeks, ~April 7, 2026)
- [ ] Fix CORS: restrict to actual frontend domains, not `allow_origins=["*"]`
- [ ] Add API key auth on `/ingest/run` and all mutation endpoints
- [ ] Switch CSV pipeline outputs to Parquet (`df.to_parquet()`)
- [ ] Build all Tier 1 ingestion scripts (see Phase 1 below)
- [ ] Train dual-model (onset + continuation)
- [ ] Stratified evaluation + SHAP side-by-side
- [ ] Event backtests (Oct 7 2023, Lebanon 2024)
- [ ] Supply chain route risk demo
- [ ] 1-page business model with TAM numbers

## Phase 1: Data Foundation — Tier 1 Sources (20 sources)

### Conflict/Ground Truth
- [ ] UCDP-GED pipeline — primary ground truth (CC BY 4.0, no legal risk)
- [ ] ACLED — keep as complement, mark EULA risk. Contact licensing: acled@acleddata.com

### Text/NLP
- [ ] GDELT GKG/GCAM: extract 2,230 emotional dimensions, filter Arabic, deduplicate, IDW interpolation
- [ ] Telegram channel monitoring: ~30 Levant channels via Telethon

### Satellite
- [ ] VIIRS Black Marble nighttime lights: daily 500m, per-hex mean + delta + anomaly
- [ ] Sentinel-2 NDVI via CDSE Statistical API: per-hex vegetation change

### Connectivity
- [ ] IODA internet outages: BGP + probing + darknet, per-country connectivity score
- [ ] Cloudflare Radar: traffic anomalies by country/ASN

### Socioeconomic
- [ ] FEWS NET/IPC food security: IPC Phase 1-5, sub-national
- [ ] WFP VAM food prices: market-level bread/fuel/rice
- [ ] LBP black market exchange rate: hourly via community APIs
- [ ] WorldPop population: 100m gridded, zonal sum per hex (one-time)

### Military/OSINT
- [ ] Pikud HaOref (IDF sirens): real-time JSON endpoint, siren count + escalation rate
- [ ] Google Trends mobilization: Hebrew (צו 8, מילואים) + Arabic (ملجأ, حرب)
- [ ] UNIFIL border incidents via ReliefWeb API

### Calendar/Context
- [ ] Religious/cultural calendar: Ramadan, Ashura, Jerusalem Day, Nakba Day, Yom Kippur
- [ ] Election windows: 90-day binary features

### Integration
- [ ] Merge all into `sentinel_v2_features.parquet`
- [ ] Verify temporal alignment: all features use t-1 data (no leakage)
- [ ] Spatial lag features: ring-1/2/3 neighbor averages

## Phase 2: Dual-Model Training
- [ ] Split data: onset set vs continuation set
- [ ] Train xgb_onset with `scale_pos_weight` ≈ negatives/positives (~200)
- [ ] Train xgb_continuation (standard, no special weighting)
- [ ] Temporal split: train 2020-01→2024-06, test 2024-07→2025-06
- [ ] Evaluate separately: onset AUC-PR, continuation AUC-PR, overall AUC-PR
- [ ] SHAP on both models (side-by-side: different features for each)
- [ ] Event backtests: known escalations with risk timeline plots
- [ ] Compare v2 to v1 baseline

## Phase 3: Post-Funding — Tier 2 Sources (27 more sources, Month 2-3)
- [ ] GPS/GNSS jamming detection (OpenSky ADS-B NACp degradation)
- [ ] NOTAMs airspace closures (FAA API / Notamify)
- [ ] OpenSky ADS-B military aircraft tracking
- [ ] TROPOMI NO2/aerosol atmospheric anomalies
- [ ] Dynamic World land cover change
- [ ] BGPStream real-time BGP monitoring
- [ ] OONI internet censorship
- [ ] Airwars geolocated airstrike data
- [ ] B'Tselem Israeli-Palestinian incidents
- [ ] UCDP ceasefire dataset
- [ ] OFAC sanctions changes
- [ ] VIEWS forecasts as ensemble input
- [ ] UNHCR refugee flows
- [ ] IOM DTM border crossings + displacement
- [ ] Microsoft Building Footprints
- [ ] UNOSAT damage labels
- [ ] OpenStreetMap infrastructure + changeset monitoring
- [ ] Arabic news RSS (Al Jazeera, Al Mayadeen, An-Nahar)
- [ ] Hebrew news RSS (Ynet, Times of Israel)
- [ ] IDF Telegram channels
- [ ] ACLED notes NLP (XLM-R embeddings)
- [ ] ReliefWeb API humanitarian reports
- [ ] MODIS snow cover (Golan/Hermon)
- [ ] OCHA FTS aid funding gaps
- [ ] INFORM Risk sub-national indicators
- [ ] Israeli GTFS-RT transit disruptions
- [ ] AIS vessel tracking (port call anomalies)

## Phase 4: Quarter 2+ — Tier 3 Sources (27 more) + Foundation Model
Tier 3 sources: Sentinel-1 SAR damage, NISAR, Reddit, UNSC transcripts, V-Dem, EPR ethnic patterns, DAHITI water levels, Freightos shipping rates, traffic anomalies, EMSC seismic, SOHR, ICG CrisisWatch, CFR Cyber Ops, DSCA arms sales, FAO prices, World Bank, GHSL, WorldCover, CAMS smoke, Ookla, Globalping, Google Transparency, GloFAS floods, SPEI drought, weather extremes, UNRWA, Meta Data for Good.

Foundation model:
- [ ] Spatial datacube (5 channels × 64×64 × 14 days at 1km)
- [ ] LSTM U-Net vs Earthformer head-to-head on onset AUC-PR
- [ ] Self-supervised MAE pretraining on multi-theater datacubes
- [ ] Meta-learner + Venn-ABERS + BCCP calibration
- [ ] Multi-theater expansion (Ukraine, Sudan, Ethiopia)

## Phase 5: Validation Suite
- [ ] Walk-forward temporal: 6 quarterly windows (2023-2024)
- [ ] Geographic CV: Lebanon ↔ Syria transfer
- [ ] Event-specific backtests with lead time measurement
- [ ] Feature ablation: remove each source group, retrain
- [ ] Feature leakage audit: all features t-1, no label leak
- [ ] Geographic equity audit: per-region accuracy
- [ ] Reproducibility: global seed, hyperparams.json, training data hash, git SHA

## Phase 6: Integration + Ethics
- [ ] Build SentinelScorer: loads best model, falls back to XGBoost
- [ ] UI: Green ≠ Safe → "No elevated risk currently detected" + uncertainty bands
- [ ] Adversary threat model documented
- [ ] Conflict redlining: commercial scores aggregated + time-delayed
- [ ] EU AI Act compliance (August 2026 deadline)
- [ ] Monthly accuracy reports including failures

## Reference
- Ground truth: UCDP-GED (CC BY 4.0). ACLED pending license.
- v1 baseline: ROC-AUC 0.872, AUC-PR 0.585. Onset AUC-PR ~0.03-0.06.
- Production model: `pipeline/models/xgb_sentinel.ubj`. Tiers: Yellow≥0.54, Orange≥0.63, Red≥0.70.
- Primary metric: **Onset AUC-PR**. Train 2020-01→2024-06. Test 2024-07→2025-06.
- Data portfolio: 74 sources, see `research/complete_data_portfolio.md`
- Business model: 3 wedges (supply chain, insurance, finance), see `research/business_model_analysis.md`
- Dead sources removed: REIGN (archived 2021), GTD (closed 2025), Polity V (frozen 2018)
