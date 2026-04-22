## Inspiration

On October 7, 2023, thousands of civilians in southern Israel had no warning. In September 2024, Hezbollah pager bombs detonated across Lebanon with zero public notice. In 2025, US-Iran tensions pushed the Strait of Hormuz to the brink — oil workers, journalists, and aid organizations operating in the region had no systematic way to know where the next flashpoint would be.

The pattern is always the same: conflict escalates gradually, the signals are there in the data — troop movements, news tone shifts, historical incident clusters — but no tool synthesizes them into something a civilian can act on. Governments get intelligence briefings. Civilians get nothing.

Sentinel is our answer to that gap.

## What it does

Sentinel monitors the Levant corridor (Lebanon, Israel, Syria) in real time, scoring every 36 km² hex on the map with a 7-day danger probability. It fuses 12+ live data streams through a dual-model ML system — XGBoost for detecting conflict **onset** (new violence in peaceful areas) and a GRU neural network for predicting conflict **continuation** (escalation in active zones). When you click any hex, a Gemini agent searches live news and writes a plain-language intelligence briefing grounded in real sources.

## How we built it

- **Dual ML architecture**: XGBoost (Optuna-tuned, 39 features) for onset prediction using an anomaly detection framing — z-scores detect when a hex is behaving unusually compared to its 30-day baseline. PerHexGRU (55K params, 83 features) for continuation prediction — a recurrent neural network that captures escalation sequences over 14-day windows. Onset AUC-PR: 0.246. Continuation AUC-PR: 0.739.
- **19 ingest scripts** across 7 data domains: conflict events (ACLED), media sentiment (GDELT dynamics), satellite (FIRMS fire, VIIRS nightlights), connectivity (IODA outages), socioeconomic (LBP exchange rate, IPC food security), military/OSINT (Pikud sirens, Google Trends mobilization), and calendar context.
- **Publication lag enforcement**: Features are shifted by their real-world availability (ACLED 3 days, GDELT 1 day) to prevent lookahead bias. This ensures the model in production sees exactly what it saw during training.
- **Backend**: FastAPI + Supabase (PostGIS), APScheduler re-scoring every 15 minutes, two-layer alerting (strategic ML + tactical rule-based).
- **Intelligence layer**: Gemini 2.5 Flash with Google Search grounding — the LLM searches real news, not hallucinations.
- **Frontend**: React + Mapbox GL JS, H3 hex overlay with YlOrRd gradient heatmap, hospital shelter layer, AI-powered evacuation routing.

## Key discoveries

- **Anomaly detection reframing** was the single biggest improvement. Instead of asking "will there be conflict?", we ask "how unusual is today compared to this hex's baseline?" Z-score features (deviation from 30-day rolling mean) became the #1 feature group, contributing more than population, spatial lags, or GDELT.
- **GRU beats XGBoost for continuation by 8.7%** because it sees escalation as a *sequence* (probe → pause → larger attack → full escalation) rather than a single row of summary statistics.
- **Most data sources are noise for onset**: Calendar features, weather, FIRMS, nightlights, food security, and Google Trends all *hurt* onset performance when added. Only z-scores, spatial lags, GDELT dynamics, population, and LBP economics help.
- **Publication lag enforcement revealed 27% metric inflation** in our continuation model's cross-validation — a critical finding for production honesty.

## What's next for Sentinel

1. **Calibrate probabilities** — make model scores meaningful (a predicted 0.7 should mean 70% chance)
2. **Register for remaining free API keys** (OpenSky ADS-B for GNSS jamming detection, Telegram for real-time OSINT, NOTAMs for airspace closures)
3. **GEE satellite features** (TROPOMI NO2, Sentinel-2 NDVI, Dynamic World) via Google Earth Engine
4. **Expand beyond the Levant** — Ukraine, Sudan, Myanmar are the next priority regions
5. **Foundation model** (post-funding) — multi-theater self-supervised pretraining with cross-modal fusion of satellite imagery, text, and tabular data
