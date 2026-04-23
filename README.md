# Sentinel — Conflict Risk Intelligence for the Levant

Aid organizations, journalists, and field teams deploy people into conflict zones every day. They make those decisions with country-level advisories that are hours old, written by analysts who aren't there. Sentinel gives them 36 km² resolution, updated every 15 minutes, 7 days ahead.

**Civilians can use it free. That's the mission. Organizations that rely on it operationally pay to sustain it.**

Charging civilians in active conflict zones for access to safety information is not a business model we're willing to build. Organizations — ICRC, MSF, Reuters, Al Jazeera, WFP — have institutional budgets for operational security tools. They are the customer. Civilians are the reason we built it.

---

## Who It's For

### Humanitarian & Aid Organizations
**ICRC, MSF, WFP, UNHCR, IRC, CARE, Oxfam**

Security coordinators making deployment decisions: can my convoy take this route today? Is our field clinic still safe to operate? Does my team need to evacuate? They currently rely on UN OCHA reports (country-level, hours old) and Dataminr (reactive news alerts, no prediction). Sentinel gives them hex-level, predictive, AI-synthesized intelligence at a fraction of the cost.

### News & Media Organizations
**Reuters, AP, AFP, Al Jazeera, BBC, NYT, Washington Post, Middle East Eye**

Bureau chiefs and security managers deciding whether to deploy journalists and fixers. A correspondent in Dahieh (southern Beirut suburb) needs different information than one in downtown Beirut — city-level advisories don't answer that question. The backtest slider also lets journalists visualize how a situation developed for data reporting.

### Security Consulting Firms
**Sibylline, Corisk, Stirling Assynt**

Boutique risk consultancies writing bespoke threat reports at $200–500/hr. Sentinel gives them a citable, structured data source with hex-level precision they can embed directly into client deliverables.

---

## What It Does

| Feature | Description |
|---|---|
| Live hex map | YlOrRd heatmap, Mapbox GL JS, H3 hex grid at resolution 5 (~36 km²) |
| Dual-model ML | XGBoost for **onset** (new violence in peaceful areas) + GRU for **continuation** (escalation in active zones) |
| AI intelligence briefs | Click any hex → Gemini 2.5 Flash searches live news and writes a plain-language brief grounded in real sources |
| Evacuation & convoy routing | Real-road routing scored for danger crossings, rerouted around Red hexes automatically |
| Multi-language | English / Hebrew / Arabic with full RTL support |
| Alert tiers | Green / Yellow / Orange / Red with rule-based tactical triggers |
| Backtest mode | Replay any date from Oct 2023 onward — watch the map evolve through documented events |
| Shelter & hospital layer | ICRC facilities, UN shelters, hospitals, border crossings |

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

The models never run together on the same hex. It's a routing decision, not an ensemble. Onset and continuation are fundamentally different problems — onset asks *is this hex behaving unusually?* (z-score anomaly signal); continuation asks *where is this trajectory heading?* (14-day sequence signal). A single model optimizing for both performs worse at both.

### Current Metrics

| Model | AUC-PR | vs. Baseline |
|---|---|---|
| Onset — XGBoost (focal loss + Optuna) | **0.246** | 11.7× (was 0.021) |
| Continuation — PerHexGRU (55K params) | **0.739** | 1.3× (was 0.56) |
| Continuation — XGBoost (Optuna) | 0.680 | GRU comparison baseline |

Publication lags enforced: ACLED +3 days, GDELT +1 day. Without enforcement, continuation CV was **27% inflated**.

### Key Discoveries

- **Anomaly detection framing was the #1 improvement.** Z-scores (how unusual is today vs. this hex's 30-day baseline?) outperform absolute values for onset. Asking "is this weird?" beats asking "is this dangerous?"
- **GRU beats XGBoost for continuation by 8.7%** — it sees escalation as a sequence (probe → pause → larger attack → full escalation), not a snapshot. XGBoost wins for onset because the 14 days before a conflict starts mostly look normal — there's no sequence to learn.
- **Most data sources are noise for onset.** Ablation testing across 16 source groups pruned 74 features down to 39. Calendar events, FIRMS fire, nightlights, and food security all *hurt* onset performance.
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

Features are ordered by how much they matter to the organizational customer.

### 1. Multi-location personnel watchlist *(most critical missing feature)*
An ICRC security officer needs to monitor 4 field clinic locations simultaneously. A Reuters bureau chief needs to track 8 journalists and fixers. Right now they'd have to click each hex individually. The watchlist lets them add locations by name or coordinate, see all of them on one screen with current risk tiers, and get alerted the moment any location escalates. This transforms Sentinel from "tool you consult" into "system you rely on."

### 2. Webhook + email alerts for watched locations
Organizations don't watch dashboards. They need push delivery: when a watched location escalates above a threshold, fire a POST to their Slack/Teams webhook, send an email to the security team, trigger PagerDuty. Webhooks (not WhatsApp) is the right delivery mechanism for institutional customers with existing incident response workflows.

### 3. Exportable situation report
Organizations have legal duty-of-care obligations. Before deploying a journalist or aid worker, they need documented evidence that a security assessment was conducted. A timestamped PDF or shareable URL containing the current hex scores, AI brief, and model metadata for a specified area. This becomes the paper trail that justifies the deployment decision — and it's a feature competitors don't offer.

### 4. REST API with authentication
Larger organizations (Reuters, AP, ICRC) will want to integrate Sentinel data into their existing systems — internal security portals, ops dashboards, incident management tools. A simple authenticated API (`GET /v1/hex/{h3_id}`, `GET /v1/region/summary`, `POST /v1/watch`) makes Sentinel infrastructure rather than just an interface. API keys + usage metering is the charging mechanism.

### 5. Multi-agent convoy and personnel movement planner *(upgrade to the current evac route)*
The current routing feature finds the safest road and generates a Gemini narrative. That's sufficient for a civilian fleeing. It is not sufficient for an MSF coordinator planning tomorrow's convoy or a bureau chief deciding whether to send a journalist tomorrow morning.

The multi-agent upgrade runs five specialized agents in parallel (~10 seconds total):

- **Route Scout** — queries Mapbox for 3–5 candidate routes, scores each segment against current hex risk tiers
- **Intelligence Agent** — Gemini + Google Search, scoped to the specific roads and towns each candidate route passes through. Asks: *"Is there active fighting on the Beirut-Damascus highway near Dahr El Ahmar right now?"* Returns per-route red flags with source timestamps
- **Forecast Agent** — uses the ML model's 14-day trend data to ask: *"Will this route be more or less dangerous by the time the convoy arrives?"* Critical for long routes where you start in a green hex and drive into a developing situation
- **Resource Agent** — checks OSM data along each route for fuel stations, hospitals, ICRC offices, border crossing status, and IODA internet coverage
- **Destination Validation Agent** — confirms the destination itself is safe and operational. An evacuation to a hospital that was struck is worse than not evacuating

A coordinator agent synthesizes all five outputs into one documented recommendation:

> *"Recommend Route B via coastal highway. Route A through the Litani crossing is 18 minutes shorter but intelligence from 2 hours ago confirms IDF activity near the junction — avoid. Route B crosses 4 low-risk hexes. ML forecast shows conditions stable for the next 11 hours; depart before 1600. Fuel available at Sidon (42km). Hammoud Hospital 55km en route. Destination ICRC Beirut office confirmed GREEN."*

That output is what a security officer needs to make and document a decision. The parallel architecture means total latency is ~10 seconds rather than 45+ for sequential calls.

### 6. ML — global training data *(highest ROI ML improvement)*
The current models train only on Levant data (~45,000 positive onset examples). ACLED covers 50+ countries going back to the 1990s — 10–20× more data, all free. Training globally teaches the model universal conflict patterns (economic stress → mobilization → onset) that it currently can't learn from three countries. Expected lift: onset AUC-PR 0.246 → 0.40–0.55. Same architecture, no infrastructure cost.

### 7. ML — text embedding features
GDELT and ACLED event descriptions are currently reduced to 6 summary numbers. A new `embed_text.py` preprocessing step runs ACLED descriptions and GDELT headlines through Gemini `text-embedding-005` (free tier), compresses to ~32 dimensions via PCA, and adds those as features to both models. The model goes from seeing `tone=-6.2` to understanding what the text actually says. Academic work shows text-only onset models reach AUC 0.83. Combined with global training, expected lift to onset AUC-PR 0.55–0.70.

### 8. ML — spatial GNN for continuation
Current spatial features are hand-crafted ring averages. A Graph Neural Network learns which neighbor relationships actually matter — violence along a highway corridor predicts downstream spread differently than violence separated by a mountain range. PyTorch Geometric, free. Expected lift: continuation 0.739 → 0.82–0.85.

### 9. UX features (free, build in parallel)
- **"Why this score?" attribution panel** — plain-language SHAP breakdown on hex click. Answers the institutional audit question: "how did you arrive at this risk level?"
- **Human toll strip** — verified ACLED fatalities and displacement counts for the current map view. Grounds risk scores in human stakes; critical for humanitarian org credibility
- **Source health drawer** — all 12 live data sources with freshness timestamps. Answers: "how current is this data?"
- **Per-hex 30-day timeline** — scrub backwards through events with ACLED citations. Lets journalists visualize how a situation developed for data reporting

---

## Competitive Landscape

What organizational customers currently use for Levant intelligence:

| Tool | Type | Weakness vs. Sentinel |
|---|---|---|
| **Dataminr** | Real-time news alerts, ~$30–50K/yr | Reactive only — no prediction. City/country level, no routing |
| **Control Risks** | Analyst reports | Hours-old, country-level, expensive, no real-time |
| **UN OCHA Security** | Free security reports | Manual, slow, country-level |
| **Internal security officers** | Human judgment | Not scalable, not always available, no ML |
| **Crisis24/GardaWorld** | Corporate security platform | Broad geography, not Levant-specialized, expensive |

Sentinel is the only predictive, real-time, hex-level conflict intelligence tool for the Levant. That's a genuine gap.

---

## Business Model

### Stage 1 — Organizations: Humanitarian + Media *(first revenue)*
Target: ICRC, MSF, WFP, Reuters, AP, Al Jazeera, BBC, Middle East Eye

These organizations already have budgets for Dataminr and Control Risks. They make deployment decisions affecting people's lives. They need what we have, and they have procurement pathways for exactly this category of tool.

| Tier | Price | Included |
|---|---|---|
| **Starter** | $500/month | 1–5 users, map + briefings, email alerts |
| **Team** | $2,000/month | 5–20 users, watchlist, webhooks, API access, exportable reports |
| **Enterprise** | $5,000–15,000/month | Unlimited users, convoy planner, priority support, custom region |

3 Team customers = $6,000/month = $72,000 ARR. That's a sustainable first milestone for a student team.

Outreach targets: "Regional Security Coordinator" at ICRC, "Bureau Security Manager" at Reuters, "Head of Access and Security" at MSF. These are specific enough roles that a personalized pitch about Levant corridor intelligence lands well.

### Stage 2 — Security Consulting Firms
Boutique consultancies — Sibylline, Corisk, Stirling Assynt — write reports citing data products. Sentinel becomes a citable source. Per-seat API access at $200–500/seat/month. Short sales cycle, no procurement review.

### Stage 3 — Enterprise
Supply chain, insurance/parametric, and alt-data finance require 6–18 month sales cycles and established revenue to enter credibly. The path is: humanitarian/media validation → consulting firm references → inbound enterprise interest.

Comps: Recorded Future ($2.65B exit), Dataminr ($4.1B), Seerist (Verisk acquisition).

---

## Funding

The ML pipeline improves for free. Funding covers hosting at scale, the satellite imagery upgrade, and the first customer acquisition.

| Item | Cost | Why |
|---|---|---|
| **Sentinel Hub Pro** | $195/month | Replaces OpenStreetMap base tiles with actual Sentinel-2 satellite imagery at 10m resolution. Users see real terrain, burn scars, destroyed neighborhoods under the hex overlay. Product credibility upgrade — ML doesn't need it, institutional buyers notice it. |
| **Supabase Pro** | $25/month | Free tier caps at 500MB and 50 concurrent connections. Required at real user scale. |
| **Backend hosting (Railway)** | $20/month | Free-tier backends sleep after inactivity. Production needs always-on. |
| **Mapbox paid tier** | $50–200/month | Free tier: 50,000 map loads/month. Paid unlocks org-level usage. |
| **Gemini API at scale** | $100/month | Free tier: ~500 hex briefings/day. Scales with usage. |
| **B2B outreach** | $3,000 one-time | Legal templates for data licensing agreements + outreach to 10 target organizations. |
| **GPU compute** | $3,000–5,000 one-time | After free ML improvements are exhausted: train a small conflict-domain foundation model on global ACLED history. Creates a technical moat. |
| **Levant domain analyst** | $5,000 one-time | Part-time regional expert to validate predictions. Credibility layer for humanitarian and media buyers. |

**6-month total: ~$15,000–20,000**

---

## Hackathon

Built at [hackathon name], **2nd place**. VCs offered a 2-week sprint to demonstrate resourcefulness before funding.