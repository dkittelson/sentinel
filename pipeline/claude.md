# Sentinel ML Pipeline — Master Reference

## Working Style
The user is learning Python, ML, and data engineering. Claude should **teach and guide**, not write code directly. Explain concepts, suggest approaches, point out pitfalls, and let the user write the code themselves.

## Current Architecture (v2, April 2026)

**Dual-model system** — two separate models for two different problems:

| | Onset Model | Continuation Model |
|---|---|---|
| **Architecture** | XGBoost (Optuna-tuned) | PerHexGRU (2-layer, 55K params) |
| **AUC-PR** | **0.246** | **0.739** |
| **Features** | 39 (anomaly detection framing) | 83 (sequential temporal patterns) |
| **What it predicts** | Violence emergence in peaceful hexes | Escalation in already-active hexes |
| **Split condition** | `dangerous_roll14d == 0` | `dangerous_roll14d > 0` |
| **Top feature group** | Z-scores (Δ+0.066 if removed) | Conflict rolling windows (Δ+0.049) |
| **Prediction horizon** | 7 days | 7 days |

### Key Design Decisions (Validated by Ablation + Benchmark)
- **XGBoost beats all neural alternatives for onset** (benchmark: RF 0.179, LightGBM 0.111, GRU crashed on 8M rows)
- **GRU beats XGBoost for continuation by 8.7%** (0.739 vs 0.680) — sequence modeling captures escalation patterns
- **Anomaly detection reframing** (z-scores) was the single biggest improvement (+30% onset AUC-PR)
- **Calendar features hurt both models** — counterintuitive but validated by ablation
- **Publication lags enforced** — ACLED features shifted by 3 days, GDELT by 1 day (prevents lookahead bias)

### Model Files
- **Onset (production):** `pipeline/models/xgb_onset.ubj` or `xgb_onset_focal.ubj`
- **Continuation (production):** `pipeline/models/per_hex_gru_best.pt`
- **Fallback:** `pipeline/models/xgb_continuation.ubj` (if PyTorch unavailable)
- **Hyperparams:** `pipeline/models/best_hyperparams.json` (Optuna-tuned)

## Data Sources

### Actively Feeding Models (12 sources)
| Source | Data | Onset? | Continuation? |
|--------|------|--------|---------------|
| ACLED conflict events | Event counts, rolling windows, velocity | Yes (spatial lags) | Yes (primary signal) |
| GDELT events | Hostility dynamics, event velocity, tone delta | Yes (#3 feature group) | Yes |
| NASA FIRMS | Fire hotspots | Yes (neighbor avg only) | Yes |
| Open-Meteo weather | Temperature, precipitation | No (noise for onset) | Yes (marginal) |
| VIIRS nightlights | NTL mean, delta, anomaly | No (noise for onset) | Yes |
| WorldPop population | Per-hex population | Yes (#2 feature group) | Yes |
| OSM infrastructure | Hospitals, schools | Yes | Yes |
| LBP exchange rate | Parallel rate, 7d/30d change, volatility | Yes (#5 feature group) | No (noise for cont) |
| Pikud HaOref | Siren counts | Yes (marginal) | Yes |
| IPC food security | IPC phases, crisis flag | No (noise for onset) | Yes |
| Google Trends | Hebrew/Arabic mobilization terms | No (too sparse) | Yes |
| Calendar | Ramadan, Ashura, Nakba Day, cyclical encoding | No (noise for both!) | No |

### Scripted But Need API Keys (7 sources)
- Cloudflare Radar (needs `CLOUDFLARE_API_TOKEN`)
- OpenSky ADS-B (needs `OPENSKY_USER`)
- Telegram channels (needs `TELEGRAM_API_ID`)
- NOTAMs airspace (needs `FAA_NOTAM_API_KEY`)
- IODA internet outages (API works, 764 events retrieved)
- ReliefWeb (API v1 deprecated, needs v2 migration)
- OFAC sanctions (too coarse for hex-level)

### 19 Ingest Scripts
`pipeline/ingest/`: adsb_military, calendar_context, cloudflare_radar, conflict_events, connectivity, fews_net, food_economic, google_trends, infrastructure, lbp_rate, maritime_transport, military_osint, notams, political_governance, population_demographic, reliefweb, satellite, telegram_monitor, text_nlp

## Feature Engineering

### Onset Features (39, ranked by ablation impact)
1. **Z-scores** (Δ+0.066): `gdelt_hostility_zscore`, `gdelt_event_count_zscore`, `neighbor_danger_zscore`, `lbp_zscore`, `firms_zscore`, `ntl_zscore`, `siren_zscore`
2. **Population** (Δ+0.048): `population_best`, `worldpop_population`, `hospital_count`, `school_count`
3. **Spatial ring-2** (Δ+0.021): `neighbor_danger_r2`
4. **Acceleration** (Δ+0.016): `gdelt_hostility_accel`, `neighbor_danger_accel`, `lbp_accel`
5. **GDELT dynamics** (Δ+0.016): `gdelt_hostility_roll3d/7d`, velocity, `gdelt_event_roll3d/7d`, velocity, `gdelt_tone_delta`
6. **Residuals** (Δ+0.015): `gdelt_hostility_residual`, `neighbor_danger_residual`, `lbp_residual`
7. **Anomaly composites** (Δ+0.014): `anomaly_count`, `max_anomaly`
8. **Actors** (Δ+0.013): `unique_actors`, `actor_pair_count`, `siren_count`
9. **Economic** (Δ+0.013): `lbp_usd_parallel`, `lbp_change_7d/30d`, `lbp_volatility_7d`
10. **Spatial ring-1** (Δ+0.012): `neighbor_danger_avg`, `neighbor_fatal_sum`, `neighbor_gdelt_hostility_avg`, `neighbor_firms_avg`, `spatial_gradient`

### Removed Features (hurt onset per ablation)
- Calendar (Δ-0.009), weather (Δ-0.005), FIRMS raw (Δ-0.004), Google Trends (Δ-0.004), NTL (Δ-0.003), interactions (Δ-0.002), raw GDELT (Δ-0.002), food security (Δ-0.001)

## Pipeline Configuration
- **H3 resolution:** 6 (~36 km² per hex, ~6.8 km edge)
- **Timeline:** 2020-01-01 to 2024-12-10
- **Label:** Binary — any dangerous event in next 7 days
- **Train cutoff:** 2024-06-10
- **Test start:** 2024-07-01
- **Temporal gap:** 21 days (prevents rolling window leakage)
- **Publication lags:** ACLED=3d, GDELT=1d (enforced in `split_data.py`)
- **Tier thresholds:** Yellow≥0.54, Orange≥0.63, Red≥0.70 (need recalibration for v2)

## Key Files
| File | Purpose |
|------|---------|
| `pipeline/train/split_data.py` | Load CSV, merge parquets, enforce pub lags, compute spatial features, z-scores, split onset/continuation |
| `pipeline/train/train_onset.py` | XGBoost onset training with Optuna params + focal loss |
| `pipeline/train/train_continuation.py` | XGBoost continuation with Optuna params |
| `pipeline/train/train_continuation_gnn.py` | PerHexGRU training for continuation |
| `pipeline/train/gnn_model.py` | Neural model definitions (GRU, GNN-LSTM, FocalLoss) |
| `pipeline/train/evaluate.py` | Metrics, calibration, SHAP, walk-forward CV, ablation, backtests |
| `pipeline/train/tune_hyperparams.py` | Optuna Bayesian hyperparameter search |
| `pipeline/train/benchmark_architectures.py` | Head-to-head architecture comparison |
| `pipeline/ml/config.py` | Centralized config (dates, lags, thresholds, seeds) |
| `backend/05_score_live.py` | Production scoring (XGBoost onset + GRU/XGBoost continuation) |

## Metrics History
| Milestone | Onset AUC-PR | Continuation AUC-PR |
|-----------|-------------|-------------------|
| Session start (v1) | 0.021 | ~0.56 |
| + Fixed pipeline + features | 0.116 | 0.654 |
| + 7-day horizon + focal loss | 0.118 | 0.654 |
| + Data expansion | 0.179 | 0.673 |
| + Ablation pruning | 0.189 | 0.663 |
| + Anomaly features + Optuna | **0.246** | 0.680 |
| + GRU for continuation | 0.246 | **0.739** |

## Next Steps (Post-Sprint)
1. **Calibrate models** — isotonic regression to make probabilities meaningful
2. **Walk-forward CV** on anomaly-feature model to get honest cross-validated numbers
3. **Register for remaining free API keys** (OpenSky, Telegram, NOTAMs)
4. **GEE satellite features** (TROPOMI NO2, Sentinel-2 NDVI, Dynamic World)
5. **GNN-LSTM** for continuation (spatial diffusion on hex graph) — Kaggle T4
6. **Foundation model** (post-funding) — multi-theater pretraining, cross-modal fusion
