# Sentinel Business Model Analysis

## Revenue Prioritization Matrix

| Segment | TAM | Near-Term Rev (Yr 1-2) | Contract Size | Sales Cycle | Priority |
|---------|-----|------------------------|---------------|-------------|----------|
| **Supply Chain Intelligence** | $3-5B | $500K-2M | $50-250K/yr | 3-6 mo | **HIGH** |
| **Insurance/Reinsurance** | $1-4B | $200K-1M | $50K-1M/yr | 6-12 mo | **HIGH** |
| **Commodity Trading/Finance** | $1-2B | $200K-500K | $50-200K/yr | 3-6 mo | **HIGH** |
| **Corporate Duty of Care** | $3-7B | $100K-500K | $10-100K/yr | 3-6 mo | **MEDIUM** |
| **Government/Defense** | $500M-1B | $150-500K | $50K-5M/yr | 6-18 mo | **MEDIUM** |
| **NGO API** | $100-200M | $50-200K | $5-50K/yr | 1-3 mo | **MEDIUM** |
| **Media/Journalism** | $10-50M | $50-200K | $1-5K/yr | 1 mo | **LOW** |
| **Academic/Research** | $50-100M | $50-200K | $5-25K/yr | 1-3 mo | **LOW** |

**Combined realistic Year 2 ARR: $1-3M | Year 4 ARR: $5-15M**

---

## 1. Supply Chain Disruption Intelligence — HIGHEST PRIORITY

### The Market
- SCRM market: $4.5B (2025), 15% CAGR → $9.2B by 2030
- SCRM software: $8.1B → $56B by 2035 (21.3% CAGR)
- Disruption events expanded 38% YoY in 2024

### Proof Points (Dollar Figures)
- **Red Sea/Houthi**: $15-20B/yr additional costs. Suez transits down 60%. Rerouting = $1.7M per voyage.
- **Russia-Ukraine**: 29% global wheat exports disrupted. Fertilizer +80%. Neon from $15→$100/liter.
- **Myanmar rare earths**: 60%+ of China's heavy rare earth supply. KIA seizure disrupted global EV/defense supply chains.
- **Sudan gum arabic**: 80-90% of world supply. No substitute for Coca-Cola/Pepsi. RSF earns $20.5M/month from transit fees.
- **Lebanon conflict**: $14B total cost (World Bank). $6.8B physical damage + $7.2B lost productivity.
- **2026 Iran**: Oil +30.7% in 17 days. 20% global LNG transits Hormuz.

### Competitors
| Company | Revenue | Valuation | Avg Contract |
|---------|---------|-----------|-------------|
| Interos | $39.7M | $1B+ | ~$80K ACV |
| Everstream | $78.1M | Undisclosed | Enterprise |
| Resilinc | Undisclosed | Established | ~$1,400/mo+ |
| Prewave | Growth stage | Undisclosed | Enterprise |

### Critical Gap Sentinel Fills
All operate at country/region level. None offer:
1. Hex-level (~36km²) granular conflict prediction
2. Forward-looking 72h prediction (vs reactive news monitoring)
3. Tactical CLEAR/WATCH/WARNING/DANGER tiers at facility/route level
4. 15-minute refresh frequency
5. Multi-source fusion (ACLED + GDELT + FIRMS + weather + satellite)

### Product Packaging
1. **Route Risk Scoring API** — segment-by-segment conflict scores along shipping corridors. $50-200K/yr.
2. **Facility/Asset Risk Monitoring** — continuous hex-level scoring for factories/warehouses/ports. $50-150K/yr.
3. **Supplier Risk Enrichment** — API feed into Resilinc, Interos, SAP Ariba. $25-100K/yr.
4. **Parametric Insurance Triggers** — objective data source for automated payouts. $200K-1M/yr.

---

## 2. Insurance & Reinsurance — HIGHEST MARGIN

### Market Sizes
- Political Risk Insurance: $1.24B → $2.2B by 2034 (5.9% CAGR)
- PRI capacity: $4B (2025). Lloyd's increased line sizes 50% ($20M→$30M) in June 2025.
- Marine War Risk: $4.1B (2024) → $7.0B by 2033 (6.2% CAGR)
- Trade Credit Insurance: ~$5B → $22B by 2035
- Parametric Insurance: $16.2B (2024), 12.6% CAGR → $34-40B by 2033

### War Risk Premium Data
- Red Sea: premiums spiked from 0.05% → 1.0% of hull value (20x increase)
- For $100M ship: $50K → $1M per voyage
- Post-ceasefire settled at 0.2% — still 4x pre-crisis
- Industry quote: "civil instability is currently so fast-changing that past trends are unreliable indicators to inform rates" — this is EXACTLY what Sentinel solves

### Parametric Insurance — The Killer App
- Trigger: "If Sentinel score > 0.70 (RED) for hex X for 3+ consecutive days → automatic payout"
- Removes claims investigation. Faster payouts. Lower admin costs.
- Nobody is doing conflict-triggered parametric insurance yet.

### Key Buyers
Lloyd's syndicates (Beazley, Hiscox, Chaucer), Munich Re, AIG/Talbot, Allianz Trade, Coface, Atradius

### Revenue Model
- Data licensing to underwriters: $50-200K/yr per syndicate
- Parametric trigger infrastructure: $200K-1M/yr
- Model validation consulting: $50-150K initial

---

## 3. Commodity Trading & Finance

### How Conflict Moves Markets
- 2026 Iran: Oil +30.7% in 17 days, urea +30% in 1 month
- Academic: 9.05% annual risk-adjusted return differential between low/high geopolitical-risk commodity futures
- 20% global LNG + 50% global urea/sulfur transit Hormuz

### Who Pays
- Bloomberg Terminal: $31,980/yr per seat. Recently added Seerist geopolitical risk scores.
- Recorded Future: acquired by Mastercard for $2.65B
- Dataminr: $222M revenue, $4.1B valuation, $282M DoD contract

### Revenue Model
- Trading signal API: $50-200K/yr per fund
- Bloomberg/Refinitiv distribution: $100-500K/yr
- Custom indices ("Sentinel Red Sea Index"): $25-100K/yr
- Hedge fund partnerships: $200K-1M/yr

---

## 4. Corporate Duty of Care (ISO 31030)

### Market
- Travel Risk Management: $3.5-3.8B → $7.4B by 2035
- International SOS alone: $1B+ revenue, 12,000 employees
- 65% of companies enhancing travel safety protocols

### Integration Targets
International SOS, Crisis24/GardaWorld (25%+ Fortune 500), Control Risks, Everbridge

### Revenue
- API feed to platforms: $25-100K/yr
- Direct enterprise: $10-50K/yr
- Travel approval workflow integration

---

## 5. Government & Defense

### Budgets
- UN OCHA/CERF: $122.8M pre-arranged for anticipatory action
- EU DG ECHO: ~$1.65B/yr humanitarian budget
- SBIR: Reauthorized through FY2031. Phase I: $50-250K, Phase II: $500K-1.5M
- OTA: AFWERX, DIU, In-Q-Tel entry points

### Contracting Paths
1. SBIR Phase I ($50-250K) — lowest barrier
2. OTA via DIU/AFWERX — prototyping contracts
3. UN OCHA anticipatory action pilots
4. EU ECHO early warning funding

---

## 6. Maritime Risk — Fastest Path to Revenue

### Key Companies
- **Dryad Global**: maritime risk intelligence + cyber. Per-vessel subscription.
- **Ambrey Intelligence**: offshore safety/security for energy/shipping.
- **CorridorRisk**: scores 7 shipping corridors every 15 min using GDELT + AIS. Closest analog to Sentinel for maritime. Open API during beta.
- **MarineTraffic/Kpler**: Risk & Compliance suite. Sanctions, AIS spoofing, port risk.
- **S&P Global MIRS**: institutional maritime intelligence.

### Sentinel Advantage over CorridorRisk
- Hex-level granularity vs corridor-level
- ML prediction vs reactive monitoring
- Multi-source fusion vs GDELT-only

---

## Three Core Revenue Wedges (VC Pitch)

### Wedge 1: Supply Chain + Maritime Risk (biggest near-term)
Red Sea/Hormuz prove the need. Ship route scoring, port disruption alerts, supplier risk enrichment. Land-and-expand with logistics companies.

### Wedge 2: Insurance Data Provider (highest margin, most defensible)
Parametric trigger infrastructure for Lloyd's syndicates. Once you're the data source for a parametric product, switching costs are enormous.

### Wedge 3: Alternative Data for Finance (highest per-seat value)
Conflict scores as trading signals via Bloomberg/Refinitiv distribution. Hedge funds pay premium for alpha-generating data.

---

## Comparable Exits
- Recorded Future: **$2.65B** (Mastercard acquisition)
- Dataminr: **$4.1B** valuation
- Interos: **$1B+** valuation
- GeoQuant: acquired by Fitch (undisclosed)
- Predata: acquired by FiscalNote

## Competitive Moats
1. **Hex-level granularity** (~36km²) — 70x finer than nearest forecasting competitor
2. **72-hour prediction** — competitors are reactive, not predictive
3. **Multi-source fusion pipeline** — hard to replicate
4. **Civilian origin story** — resonates with humanitarian AND enterprise buyers
5. **Human feedback loop** — more users → better labels → better model → more users
