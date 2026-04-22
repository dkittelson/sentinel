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
| Real-time briefings | Click any hex → Gemini 2.5 Flash searches live news and writes a plain-language intelligence brief |
| Evacuation routing | Hospital and shelter layer with AI-powered route recommendations |
| Multi-language | English / Hebrew / Arabic with full RTL support |
| Alert tiers | Green / Yellow / Orange / Red with rule-based tactical triggers |

---

## ML Pipeline

### Architecture

Every hex is routed to one of two models based on its recent history:

```
Hex is peaceful (no events in past 14 days)?
  → Onset XGBoost: 39 features, anomaly detection framing
    "Is something about to START here?"

Hex is active (violence in past 14 days)?
  → Continuation GRU: 83 features, 14-day sequence window
    "Is this about to ESCALATE?"
```

The models never run together on the same hex. It's a routing decision, not an ensemble.

### Why two separate models?

Onset and continuation are fundamentally different problems. Onset asks *is this hex behaving unusually?* — the signal is anomaly (z-scores vs. 30-day baseline). Continuation asks *where is this trajectory heading?* — the signal is sequence (14 days of escalation history). A single model trying to learn both gets worse at both.

### Current Metrics

| Model | AUC-PR | vs. Baseline |
|---|---|---|
| Onset — XGBoost (focal loss + Optuna) | **0.246** | 11.7× (was 0.021) |
| Continuation — PerHexGRU (55K params) | **0.739** | 1.3× (was 0.56) |
| Continuation — XGBoost (Optuna) | 0.680 | baseline for GRU comparison |

Publication lags enforced: ACLED +3 days, GDELT +1 day. Without enforcement, continuation CV was **27% inflated** — a critical production honesty guarantee.

### Key Discoveries

- **Anomaly detection framing was the #1 improvement.** Z-scores (how unusual is today vs. this hex's 30-day baseline?) outperform absolute values. Asking "is this weird?" beats asking "is this dangerous?"
- **GRU beats XGBoost for continuation by 8.7%** — it sees escalation as a sequence (probe → pause → larger attack → full escalation), not a snapshot.
- **Most data sources are noise for onset.** Ablation testing across 16 source groups pruned 74 features down to 39. Calendar features, weather, FIRMS, nightlights, and food security all *hurt* onset when added.
- **Publication lag enforcement matters.** Without it, metrics are inflated by up to 27%.

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

### Free to build — ordered by expected ROI

**ML**

1. **Global ACLED training** *(highest impact, zero cost)* — Keep the exact same XGBoost/GRU architecture. Train on ACLED data from 50+ countries instead of just the Levant. This gives 10–20× more positive examples and teaches the model universal conflict patterns (economic stress → mobilization → onset) rather than just Levant-specific ones. Expected lift: onset AUC-PR 0.246 → 0.40–0.55.

2. **Text embedding features** — GDELT and ACLED descriptions are currently reduced to 6 summary numbers (tone, hostility count, etc.). We throw away 99% of the information. Instead: run ACLED event descriptions and GDELT headlines through Gemini `text-embedding-005` (free), compress to ~32 dimensions via PCA, add as new features to XGBoost. The model goes from seeing "tone=-6.2" to understanding what the text actually says. Academic work shows text-only onset models reach AUC 0.83. Expected lift: onset 0.246 → 0.35–0.50. Combined with global training: 0.55–0.70.

3. **Spatial GNN for continuation** — Current spatial features are hand-crafted ring averages (ring-1, ring-2 neighbor means). A Graph Neural Network learns *which* neighbor relationships matter from data — violence along a highway corridor is more predictive than violence separated by a mountain range. PyTorch Geometric, free. Expected lift: continuation 0.739 → 0.82–0.85.

4. **Calibrated probabilities** — Add Venn-ABERS calibration so model scores are statistically meaningful (0.70 should mean 70% chance). Required for the insurance/parametric trigger wedge.

**Fullstack**

- [ ] **WhatsApp / SMS civilian alerts** — opt-in phone + hex threshold; alert when score crosses. Twilio free tier + WhatsApp Business API free up to 1,000 conversations/month.
- [ ] **Parametric insurance webhook** — `POST /v1/triggers`: fire a webhook when hex score > threshold for N consecutive days. Live demo of the B2B thesis.

**UX (5 features, all free to build)**

1. **"Why this score?" attribution panel** — click any hex → plain-language SHAP breakdown of the top 3 drivers. Removes the black-box problem.
2. **Human toll strip** — a thin, dignified band showing verified fatalities and displacement for hexes in the current map view. Grounds abstract risk scores in human stakes.
3. **Source health drawer** — shows all 12 live sources with last-update timestamps and freshness badges. Answers the question: "how do we know this data is current?"
4. **Similar historical pattern match** — surface the top-3 most similar 14-day trajectories from history. *"This pattern resembles southern Lebanon, July 2006."*
5. **Per-hex 30-day timeline scrub** — date slider that animates events in/out. Turns the dataset into a browseable archive.

### With funding

The ML pipeline improves for free. Funding covers three things: product presentation, hosting at scale, and customer acquisition.

| Item | Cost | Why it matters |
|---|---|---|
| **Sentinel Hub Exploration** | $195/month | Swaps the base map from OpenStreetMap tiles to actual Sentinel-2 satellite imagery (10m resolution). Users see real terrain, burn scars, destroyed neighborhoods — not just colored hexes. This is entirely a product presentation upgrade; the ML doesn't need it. |
| **Supabase Pro** | $25/month | Free tier caps at 500MB and 50 concurrent connections. Needed when real users arrive. |
| **Backend hosting (Railway)** | $20/month | Free-tier backends sleep after inactivity. Always-on needed for production. |
| **Mapbox paid tier** | $50–200/month | Free tier caps at 50,000 map loads/month (~1,600 users/day). Costs scale with usage. |
| **Gemini API at user scale** | $50–100/month | Free tier allows ~500 hex briefings/day. At real usage, this becomes a cost. |
| **Twilio (SMS/WhatsApp at scale)** | $50/month | Free trial covers the demo. Production alerts cost ~$0.008/message. |
| **B2B outreach** | $3,000 one-time | Legal templates for data licensing agreements + 10 consulting firm meetings. |
| **GPU compute (contrastive pretraining)** | $3,000–5,000 one-time | After free-data ML is exhausted: train a small conflict-domain foundation model from scratch on global ACLED history. This creates a technical moat. |
| **Levant domain analyst** | $5,000 one-time | Part-time regional expert for ground-truth validation. Critical for journalist and consulting firm credibility. |

**6-month total at real product scale: ~$15,000–20,000**

---

## Business Model

Three stages, ordered by sales cycle and reachability:

### Stage 1 — Civilians & Journalists (now, free product)
Build credibility through real use. Journalists at Reuters, AP, and BBC are already in the Levant — a tool that scores their exact hex drives press coverage, which drives everything downstream. No sales cycle. No contract. Just a product good enough that people talk about it.

### Stage 2 — Small Security Consulting Firms (first revenue)
Boutique risk consultancies — Sibylline, Corisk, Stirling Assynt, and dozens like them — write bespoke threat reports for corporate clients at $200–500/hr. They need structured, citable data sources. Sentinel gives them hex-level risk scores they can embed directly into client reports.

| Offering | Price | Why it works |
|---|---|---|
| Per-seat API access | $200–500/seat/month | Analyst tool — replaces manual OSINT aggregation |
| White-label report data | $2–5K/month | Firm cites "Sentinel data" in deliverables to clients |

These firms move fast (no procurement, no security review), validate the product in professional context, and create a reference customer list before approaching larger buyers.

### Stage 3 — Enterprise (after validation)
Supply chain, insurance/parametric, and alt-data finance are the long-term wedges — but they require 6–18 month sales cycles and existing revenue to credibly enter. The path is: press coverage → consulting firm validation → inbound enterprise interest.

Comps: Recorded Future ($2.65B exit), Dataminr ($4.1B), Seerist (Verisk acquisition).

---

## Hackathon

Built at [hackathon name], **2nd place**. VCs offered a 2-week sprint to demonstrate resourcefulness before funding.