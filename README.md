# Sentinel — Conflict Risk Intelligence for the Levant

Civilians in conflict zones get nothing. Governments get intelligence briefings. Sentinel closes that gap.

When Hezbollah pager bombs detonated across Lebanon in September 2024, there was zero public warning. When US-Iran tensions pushed the Strait of Hormuz to the brink in 2025, oil workers and journalists had no systematic way to know where the next flashpoint would be. The signals are always in the data — the tools to read them aren't.

**Sentinel scores every 36 km² hex across Lebanon, Israel, and Syria with a 7-day conflict probability, updated every 15 minutes, using only free public data.**

---

## What It Does

| Feature | Description |
|---|---|
| Live hex map | YlOrRd heatmap, Mapbox GL JS, H3 hex grid at resolution 5 (~36 km²) |
| Dual-model ML | XGBoost for **onset** (new violence in peaceful areas) + GRU for **continuation** (escalation in active zones) |
| Real-time briefings | Click any hex → Gemini 2.5 Flash searches live news and writes a plain-language summary |
| Evacuation routing | Hospital and shelter layer with AI-powered route recommendations |
| Multi-language | English / Hebrew / Arabic with full RTL support |
| Alert tiers | Green / Yellow / Orange / Red with rule-based tactical triggers |

---

## ML Pipeline

### Architecture

```
Hex is peaceful?  →  Onset XGBoost (39 features, anomaly detection framing)
Hex is active?    →  Continuation GRU (83 features, 14-day sequence window)
```

### Current Metrics

| Model | AUC-PR | vs. Baseline |
|---|---|---|
| Onset — XGBoost (focal loss + Optuna) | **0.246** | 11.7× (was 0.021) |
| Continuation — PerHexGRU (55K params) | **0.739** | 1.3× (was 0.56) |
| Continuation — XGBoost (Optuna) | 0.680 | baseline for GRU comparison |

Publication lags enforced: ACLED +3 days, GDELT +1 day. Without enforcement, continuation CV was **27% inflated**.

### Key Discoveries

- **Anomaly detection framing was the #1 improvement.** Z-scores (how unusual is today vs. this hex's 30-day baseline?) outperform absolute values across all onset feature groups. Asking "is this weird?" beats asking "is this dangerous?"
- **GRU beats XGBoost for continuation by 8.7%** — it sees escalation as a sequence (probe → pause → larger attack → full escalation), not a snapshot.
- **Most data sources are noise for onset.** Ablation testing across 16 source groups pruned 74 features down to 39. Calendar features, weather, FIRMS, nightlights, and food security all *hurt* onset when added.
- **Publication lag enforcement matters.** Without it, metrics are artificially inflated by up to 27%. This is our production honesty guarantee.

### Data Sources (19 ingest scripts)

| Domain | Sources |
|---|---|
| Conflict events | ACLED, UCDP-GED |
| Media sentiment | GDELT dynamics (hostility, tone, velocity) |
| Satellite | FIRMS fire, VIIRS nightlights |
| Connectivity | IODA internet outages |
| Socioeconomic | LBP exchange rate, IPC food security |
| Military/OSINT | Pikud HaOref sirens, Google Trends mobilization |
| Infrastructure | OSM hospitals/schools, WorldPop population |

---

## Stack

- **Backend**: FastAPI + Supabase (PostGIS) + APScheduler (15-min re-scoring)
- **Frontend**: Vite + React + Mapbox GL JS + h3-js
- **ML**: XGBoost + PyTorch (GRU) + Optuna + SHAP
- **Intelligence**: Gemini 2.5 Flash with Google Search grounding

---

## Roadmap

### Free to build (no funding required)

**ML**
- [ ] **Text embedding features** — generate embeddings from ACLED event descriptions and GDELT headlines using Gemini `text-embedding-005` (free tier); feed as ~32 PCA'd features into XGBoost. Academic work shows text-only onset models reach AUC 0.83. Expected lift: onset AUC-PR 0.246 → 0.35+.
- [ ] **Calibrated probabilities** — add Venn-ABERS calibration so model scores are statistically meaningful (0.7 should mean 70% chance). Required for the insurance/parametric trigger wedge.

**Fullstack**
- [ ] **WhatsApp / SMS civilian alerts** — opt-in phone number + hex threshold selection; push alert when score crosses. Twilio free tier + WhatsApp Business API free up to 1,000 conversations/month. Works offline on a dumbphone — critical for the Levant.
- [ ] **Parametric insurance webhook demo** — `POST /v1/triggers`: fire a webhook when hex score > threshold for N consecutive days. Demo-able live: shows the B2B data product thesis in 30 seconds.

**UX (5 features, all free)**
1. **"Why this score?" attribution panel** — click any hex → plain-language SHAP breakdown: "45% from ACLED event 12km away, 30% from GDELT tone acceleration, 18% from nightlight anomaly." Builds trust; removes the black-box problem.
2. **Human toll strip** — a thin, dignified band showing ACLED-verified fatalities and displacement for the past 7 days in the current map view. Grounds abstract risk scores in human stakes.
3. **Source health drawer** — collapsible panel showing all 12 live sources with last-update timestamp and freshness badge (live / stale / offline). Answers the B2B audit question: "how do we know your data is fresh?"
4. **Similar historical pattern match** — for any hex, surface the top-3 most similar 14-day trajectories from the historical record. E.g., "This pattern resembles southern Lebanon, July 2006." Informative and emotionally resonant.
5. **Per-hex 30-day timeline scrub** — bottom drawer with a date slider. Scrub backwards to watch events animate in/out with inline ACLED citations. Turns the dataset into a browseable archive.

### With funding (~$30K)

| Use | Cost | What it unlocks |
|---|---|---|
| 3 paid B2B pilots | ~$12K (sales + legal templates) | Revenue validation → Series seed story |
| Sentinel Hub Pro satellite data | ~$500/mo | Real-time satellite damage + NDVI layers in the map |
| GPU compute budget | ~$5K | Larger embedding models, faster GRU iteration |
| Levant domain analyst (part-time) | ~$5K | Ground-truth validation → credibility for insurance/NGO buyers |

---

## Business Model

Three revenue wedges targeting organizations that price geopolitical risk:

| Wedge | Buyers | Angle | TAM |
|---|---|---|---|
| Supply chain | Logistics, shipping, commodities | 70× finer resolution than competitors; 72h forward (reactive tools only react) | $3–5B SCRM market |
| Insurance / parametric | Lloyd's syndicates, Munich Re, AIG | Automated payout triggers; removes claims investigation | $1–4B political risk + marine war |
| Alternative data / finance | Hedge funds, Bloomberg/Refinitiv distributors | Conflict scores as trading signals; 9.05% risk-adjusted return differential (academic) | $1–2B alt-data |

Comps: Recorded Future ($2.65B exit), Dataminr ($4.1B), Seerist (Verisk acquisition).

---

## Hackathon

Built at [hackathon name], **2nd place**. VCs offered a 2-week sprint to demonstrate resourcefulness before funding.