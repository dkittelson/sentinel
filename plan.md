# Sentinel — Company Plan

## Identity
**Conflict risk intelligence platform.** Hex-level risk scores (~36km²), daily, 72-hour prediction.
One engine, three products: API (revenue), Dashboard (institutional), Alerts (free, civilian mission).
"Conflict Risk Intelligence" — not early warning, not defense, not prediction engine.

## Revenue — Three Wedges (Priority Order)

### Wedge 1: Insurance Data Provider ($1-4B TAM, highest margin) — FIRST REVENUE
- Parametric trigger infrastructure for Lloyd's syndicates (auto-payout when score hits RED)
- War risk underwriting data (premiums spiked 20x during Red Sea crisis, Hormuz premiums at 1-7.5% in March 2026)
- Data licensing to underwriters: $75-150K/yr per syndicate
- Nobody does conflict-triggered parametric insurance yet — greenfield opportunity.
- **Why first:** Fastest sales cycle (2-4 months), underwriters repricing weekly, desperate for forward-looking data.
- **Entry:** Lloyd's Lab accelerator → warm intros to every marine war risk underwriter in London.

### Wedge 2: Supply Chain Risk Intelligence ($3-5B TAM) — BIGGEST NEAR-TERM TAM
- Route risk scoring API for shipping corridors (Red Sea, Suez, E. Mediterranean)
- Facility/asset risk monitoring for factories, warehouses, ports
- Supplier risk enrichment feed into Resilinc, Interos, SAP Ariba
- $30-60K/yr for API. Red Sea rerouting still costing $80-100B/yr globally.
- **Position as data layer/API, NOT a full supply chain platform.**

### Wedge 3: Alternative Data for Finance ($1-2B TAM) — HIGHEST PER-SEAT VALUE
- Trading signal API for hedge funds: $150-300K/yr per fund
- Bloomberg/Refinitiv distribution: $100-500K/yr (30-40% rev share)
- Custom indices ("Sentinel Red Sea Index"): $25-100K/yr, long-term CME/ICE futures licensing
- **Requires 3-5 year backtest dataset before first sale — build this during sprint.**

### Other Revenue
- **Tier 0 (FREE):** Humanitarian co-build (iMMAP/REACH/Insecurity Insight). Credibility infrastructure.
- **Tier 1 ($20-50K/yr):** Corporate duty-of-care (ISO 31030). Media, NGOs, consulting firms.
- **Government:** SBIR Phase I ($50-250K), OTA via DIU/AFWERX, UN OCHA anticipatory action.

**Comparable exits:** Recorded Future ($2.65B), Dataminr ($4.1B), Interos ($1B+), GeoQuant (Fitch).
**Realistic projections:** Year 2 ARR $1-3M, Year 4 ARR $5-15M.

## Data Portfolio
**74 data sources** across 6 domains. See `research/complete_data_portfolio.md`.
- **Tier 1 (2-week sprint):** 22 sources — UCDP-GED, GDELT GKG, VIIRS NTL, IODA, Cloudflare, FEWS NET, WFP prices, LBP rate, Pikud HaOref, Google Trends, UNIFIL, Telegram, Sentinel-2 NDVI, WorldPop, calendar features, **IMF PortWatch** (2,033 ports + Suez chokepoint), **aisstream.io** (coastal AIS for supply chain demo)
- **Tier 2 (post-funding):** 27 more — GPS jamming, NOTAMs, ADS-B military, TROPOMI, sanctions, refugee flows, building footprints, ceasefire data, transit disruptions
- **Tier 3 (quarter 2+):** 27 more — SAR damage, NISAR, Reddit, V-Dem, EMSC seismic, shipping rates

## Architecture

### Current (v2 target — 2-week sprint)
**Dual-model XGBoost** — two separate models:
- **Onset model:** Predicts violence in peaceful hexes. Trained on GDELT GKG emotions, IODA connectivity, food prices, currency, Google Trends mobilization, spatial lag, nightlight trends, calendar. `scale_pos_weight` or focal loss.
- **Continuation model:** Predicts escalation in active hexes. Trained on lagged violence, rolling counts, FIRMS, nightlight drops.
- **Scoring:** peaceful hex → onset model; active hex → continuation model.

### Post-Funding (Month 3+)
- **Branch A — Spatial model** (5-10M params). LSTM U-Net vs Earthformer on 5-channel datacube.
- **Branch B — Enhanced onset detector** with XLM-R text embeddings + all Tier 2 features.
- **Meta-learner + Venn-ABERS + BCCP calibration.**
- **Ground truth: UCDP-GED (CC BY 4.0).** ACLED pending commercial license.

## Implementation Roadmap

### 2-Week VC Sprint (~April 7, 2026)
- [ ] Build 11 ingestion scripts covering 20 Tier 1 sources
- [ ] Train dual-model (onset + continuation XGBoost)
- [ ] Stratified evaluation + SHAP side-by-side
- [ ] Event backtests (Oct 7 2023, Lebanon 2024 escalation)
- [ ] Supply chain route risk demo
- [ ] 1-page business model with TAM numbers + comparable exits
- [ ] Fix CORS + API auth bugs

### Month 2-3: Tier 2 Integration (27 more sources)
- [ ] Add all Tier 2 functions to existing ingestion scripts
- [ ] XLM-R text encoder for ACLED notes + GDELT titles
- [ ] Begin humanitarian partner outreach (3-5 orgs)
- [ ] Start EU AI Act documentation
- [ ] Monthly accuracy reports publishing

### Month 4-6: Foundation Model
- [ ] Build spatial datacube (5 channels × 64×64 × 14 days)
- [ ] LSTM U-Net vs Earthformer head-to-head
- [ ] Self-supervised MAE pretraining on multi-theater datacubes
- [ ] Multi-theater expansion (Ukraine, Sudan, Ethiopia)

### Month 6-9: Validation + Production
- [ ] Meta-learner + calibration integrated
- [ ] Walk-forward temporal validation
- [ ] Geographic equity audit
- [ ] EU AI Act conformity assessment (August 2026 deadline)

### Month 1-3 Post-Sprint: First Revenue Push
- [ ] Apply to Lloyd's Lab accelerator (insurance wedge entry point)
- [ ] Free pilot to INSO + iMMAP + REACH (credibility infrastructure)
- [ ] Build event-price correlation backtest (Brent, CDS, freight vs scores)
- [ ] Outreach to 3 Lloyd's marine war risk syndicates (Canopius, Beazley, Ascot)
- [ ] Build "Sentinel Red Sea Risk Index" prototype

### Month 3-6: Expand Revenue Channels
- [ ] First paying insurance customer ($75-150K/yr)
- [ ] Outreach to ZIM Shipping + Energean (supply chain wedge)
- [ ] Approach Riskline/Everbridge for data feed partnership (corporate duty-of-care scale)
- [ ] Submit to Bloomberg Data License evaluation (finance distribution)

### Month 6-12: Scale
- [ ] 3-5 paying customers across insurance + supply chain
- [ ] Publish peer-reviewed methodology paper
- [ ] Find business co-founder for enterprise sales
- [ ] Begin commodity trading house outreach (Vitol, Trafigura — finance wedge)

## Validation Protocol (Pre-Registered)
**Primary metric: Onset AUC-PR** (onset set: hex-days where dangerous_roll14d == 0).
Hit: score exceeded threshold within 72h BEFORE event, same hex or ring-1 neighbor.
Baselines: persistence, conflict-history-only XGBoost, text-only onset.
Published before live scoring. Cannot be adjusted post-hoc.

## Ethics
- Decision SUPPORT only. Never "evacuate immediately." Never "Green = Safe."
- No targeting systems. Civilian protection only.
- Conflict redlining prevention: no raw hex-level scores to insurers. Aggregate + time-delay for commercial.
- Authenticate all endpoints. Adversary threat model. Geographic equity audit.
- Monthly accuracy reports including failures. Quarterly ethics review.
- EU AI Act compliance from Day 1 (logging, documentation, human oversight, transparency).

## Product Architecture — One Engine, Multiple APIs

One core engine powers every customer segment. No separate systems.

```
              ┌───────────────────────────────┐
              │       SENTINEL CORE ENGINE    │
              │  Data Ingestion → ML Scoring  │
              │  → Hex Scores → Tactical Tiers│
              └──────────────┬────────────────┘
                             │
         ┌──────────┬────────┴───────┬──────────────┐
         ▼          ▼                ▼              ▼
   ┌──────────┐ ┌────────────┐ ┌──────────┐ ┌───────────┐
   │ Civilian │ │ Supply     │ │Insurance │ │ Finance   │
   │ App      │ │ Chain API  │ │ API      │ │ API       │
   └──────────┘ └────────────┘ └──────────┘ └───────────┘
```

What changes per audience:
- **Which endpoints** they access (route scoring vs hex scoring vs index values)
- **What data overlays** (ports/shipping lanes, JWC listed areas, commodity prices)
- **Output format** (map for civilians, JSON for developers, Oasis LMF for insurers)
- **Time horizon** (72h for civilians, corridor-level for shipping, historical backtest for quants)

### Audience-Specific Endpoints & Data Requirements

#### 1. Insurance API (PRIORITY — fastest revenue)
**What underwriters need from Sentinel:**
- Hex-level + corridor-level risk scores (current + 72h forecast)
- Parametric trigger feeds: score > threshold for N days → event trigger
- JWC Listed Area overlay (geocoded, shows when scores predicted JWC changes)
- Actuarial-grade calibration: precision-recall curves, Brier scores, confidence intervals
- Audit trail: every score timestamped, model version logged (Solvency II Articles 82/121)
- Output in Oasis LMF / OED format so insurers can import into RMS/AIR workflows

**Data sources needed (beyond core):**
| Source | Why | Cost | Status |
|--------|-----|------|--------|
| JWC Listed Areas (geocoded) | Credibility with marine underwriters | Free | **ADD NOW** |
| IMF PortWatch | Port disruption context for marine risk | Free | **ADD NOW** |
| AIS satellite (Kpler/Datalastic) | Vessel tracking for marine war risk | 80-1000+ EUR/mo | Add when revenue justifies |
| Windward Maritime AI | Dark shipping, sanctions, vessel risk | Enterprise | Add when revenue justifies |
| Oasis LMF output format | Insurers can import your data into their tools | Free (open source) | Build post-funding |

**Go-to-market:** Apply to Lloyd's Lab accelerator → 90-day trials with syndicates (Canopius, Beazley, Ascot) → $75-150K/yr per syndicate.

#### 2. Supply Chain API
**What logistics/shipping companies need:**
- Route risk scoring: segment-by-segment conflict scores along shipping corridors
- Facility/asset risk monitoring: continuous hex-level scoring for factories, warehouses, ports
- Port disruption alerts: congestion, closure, transit volume drops
- Webhook alerts when hexes along their routes transition tiers (CLEAR→WATCH→WARNING→DANGER)

**Data sources needed (beyond core):**
| Source | Why | Cost | Status |
|--------|-----|------|--------|
| IMF PortWatch | 2,033 ports + 28 chokepoints + Suez transits | Free | **ADD NOW** |
| AIS vessel tracking (aisstream.io) | Coastal vessel positions for demo/MVP | Free | Already in portfolio (Tier 3) — **PROMOTE to Tier 1** |
| AIS satellite (Kpler/Datalastic) | Open-ocean tracking for paying customers | 80-1000+ EUR/mo | Add when revenue justifies |
| Freightos Baltic Index | Container freight rate spikes | Free tier available | Already in portfolio |
| OFAC/OpenSanctions | Sanctions compliance overlay | Free | Already in portfolio (Tier 2) |

**Go-to-market:** Plug and Play Supply Chain accelerator, maritime conferences → ZIM, Agility Logistics, Energean → $30-60K/yr.

#### 3. Finance API
**What quant funds and commodity traders need:**
- Real-time hex scores via REST API (JSON) — 15-min refresh is excellent
- Historical backfill: 3-5 years of backtested scores (MANDATORY — no fund buys without this)
- S3/GCS bucket drops: daily Parquet files for data lake ingestion
- Custom indices: "Sentinel Red Sea Risk Index", "Sentinel Levant Conflict Index"
- Event-price correlation: proof that scores predict Brent, CDS, freight rate movements
- Confidence intervals + model versioning metadata

**Data sources needed (beyond core):**
| Source | Why | Cost | Status |
|--------|-----|------|--------|
| CFR Sovereign Risk Tracker | CDS spread proxy — validates score→financial impact | Free | **ADD NOW** |
| Commodity prices (Commodities-API) | Brent crude, wheat, LNG for correlation | Free tier | **ADD NOW** |
| POLECAT (ICEWS successor) | Better-coded events for backtest accuracy | Free (Harvard Dataverse) | **ADD NOW** |
| IMF PortWatch | Suez transit data for Red Sea index | Free | **ADD NOW** |
| Bloomberg Data License | Distribution to 300K+ terminals | 30-40% rev share | Apply post-funding |

**Go-to-market:** Build backtest → outreach to commodity trading houses (Vitol, Trafigura) → Bloomberg Data License application → $150-300K/yr.

#### 4. Corporate Duty-of-Care API
**What GSOCs and travel risk platforms need:**
- Real-time hex scores + tactical tiers for employee locations
- Webhook alerts: push to Everbridge/AlertMedia when risk changes near travelers
- Evacuation routing (Sentinel's unique differentiator — nobody else has this)
- Pre-trip risk assessments: score any lat/lon for travel approval workflows
- Integration with HR/travel booking (SAP Concur, Navan)

**Data sources needed (beyond core):**
No additional data sources needed. Core engine + evacuation routing covers this entirely.

**Go-to-market:** Sell as data feed to Riskline/Everbridge/Crisis24 (one deal = hundreds of end-users) → direct to media safety desks (Reuters, BBC) → oil & gas GSOCs → $10-100K/yr direct, $100K-1M/yr via platforms.

#### 5. Humanitarian (Free Tier — Credibility Infrastructure)
**What NGOs/UN agencies need:**
- Free dashboard + basic API access
- Sub-national resolution (hex-level exceeds all existing tools)
- HDX/HAPI integration for data sharing
- Published, transparent methodology (addresses OCHA's 2022 skepticism)
- Tactical tiers (CLEAR/WATCH/WARNING/DANGER) with human-in-the-loop design

**Data sources needed (beyond core):**
No additional sources. Core engine is already optimized for humanitarian use.

**Go-to-market:** Free pilots with iMMAP + REACH + INSO → OCHA Centre for Humanitarian Data evaluation → EU DG ECHO innovation funding.

### Data Sources Summary — What to Add Now

| Source | Serves | Cost | Integration Effort |
|--------|--------|------|-------------------|
| **IMF PortWatch** | Insurance, Supply Chain, Finance | Free | 1-2 days |
| **POLECAT** (Harvard Dataverse) | Finance, All (validation) | Free | 2-3 days |
| **JWC Listed Areas** (geocoded) | Insurance | Free | 0.5 day |
| **CFR Sovereign Risk Tracker** | Finance | Free | 0.5 day |
| **Commodity prices** (free API) | Finance | Free | 0.5 day |
| **aisstream.io** (promote from Tier 3) | Supply Chain | Free | 1-2 days |
| **Total** | | **$0** | **~7 days** |

## Key Decisions
- H3 res 6, daily grain, 72h label. UCDP-GED primary ground truth (CC BY 4.0).
- Dual-model onset + continuation XGBoost for v2.
- Foundation model (spatial) deferred to post-funding. Built properly over 6-12 months.
- Consumer app is free mission. Revenue from API to supply chain + insurers + finance.
- Humanitarian partnerships are credibility infrastructure, not revenue.
- One core engine, audience-specific API endpoints and data overlays. Never separate systems.
- Insurance is the priority revenue wedge (fastest close, highest margin, greenfield for parametric).
- Dead sources removed: REIGN (archived 2021), GTD (closed 2025), Polity V (frozen 2018, use V-Dem).
