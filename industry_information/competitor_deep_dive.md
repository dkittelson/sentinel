# Competitor & Platform Deep Dive — Conflict Maps and Risk Intelligence

*Research compiled March 2026. Supplements `internet_info.md` with per-platform operational detail.*

---

## 1. LiveUAMap (liveuamap.com)

**What it is:** Nonprofit, volunteer-run civic journalism project founded in 2014 during the Crimea crisis. Interactive map plotting conflict events in near-real-time. Covers Ukraine, Middle East, Syria, Africa, and more via separate map instances.

**Data sources:**
- Open sources: social media (Twitter/X, Telegram), news agencies, official government statements, eyewitness reports
- No proprietary sensors or paid data feeds
- Algorithmic filtering + human editorial curation to geolocate and verify events
- Originally experimented with algorithms to correlate social media posts to geographic locations

**Data pipeline:**
- Semi-automated: algorithms surface candidate events from social media firehose, human editors verify and pin to map
- Events tagged with source links, timestamps, and categories (military action, humanitarian, political)
- No predictive layer -- purely retrospective event plotting

**Revenue model:**
- Ad-supported free tier (primary revenue)
- PRO subscription: ad-free experience, satellite map overlays, location search, historical timeline access
- API licensing: charged per-use, enterprise pricing available with volume discounts (PayPal/SWIFT invoicing)
- Enterprise services: advanced social media data mining and analysis for defined geographic areas

**Target customers:**
- General public, journalists, OSINT researchers (free tier)
- Newsrooms, think tanks, security analysts (PRO)
- Defense/intelligence contractors, media companies (API/Enterprise)

**What Sentinel can learn:**
- Speed matters: LiveUAMap's value is immediacy -- events appear within minutes of social media reports
- Source transparency: every pin links back to its source, building trust
- Regional map instances (separate maps per conflict zone) reduce information overload
- Low barrier to entry: free access built a massive audience that funds the operation

**Gaps Sentinel could fill:**
- LiveUAMap has ZERO prediction -- it only shows what already happened
- No risk scoring, no alert tiers, no evacuation routing
- No structured data export for programmatic use (beyond expensive API)
- No civilian-actionable guidance (just raw event pins)
- No aggregation into risk zones -- every event is a discrete point

---

## 2. ACLED Dashboard & Products

**What it is:** The Armed Conflict Location & Event Data Project. Originally an academic dataset (founded 2005, Clionadh Raleigh at Sussex), now a major data organization. Covers political violence and protest events globally with structured, coded data.

**Data sources:**
- ~100+ researchers coding events from local/regional/international media, NGO reports, government sources
- Sources vary by country: local newspapers, wire services (Reuters, AFP), humanitarian situation reports
- Human coders apply a standardized codebook (event type, actors, fatalities, location, notes)
- All sources are FREE to ACLED -- they're coding publicly available information

- Coverage: 250+ countries/territories, updated weekly with ~1 week lag

**Full product suite:**
1. **ACLED Data (core):** Downloadable CSV/API of all coded events. Free for academic/personal use. Corporate license required for commercial use.
2. **ACLED Explorer:** Interactive web dashboard for filtering by location, actor, event type. Exportable charts/tables.
3. **ACLED Trendfinder:** Trend tracking for political violence and demonstrations over time.
4. **CAST (Conflict Alert System):** LightGBM forecasts at Admin1 level, four-week rolling windows, up to 6 months ahead. Uses Tweedie objective with conformal inference for uncertainty.
5. **Conflict Exposure Calculator:** Assesses population exposure to conflict within defined areas and timeframes.
6. **Conflict Index:** Composite scoring.
7. **Early Warning Dashboard:** Merged hub housing Trendfinder, CAST, Exposure Calculator, and Conflict Index.
8. **Analysis reports:** Regional/thematic reports (free), deep-dive country reports.

**Pricing / revenue:**
- Free tier: academic, personal, media use (requires myACLED registration, rate-limited API)
- Commercial license: required for any corporate/government use. Pricing NOT public -- negotiated per-client. Estimated range from industry sources: $10K-$100K+/year depending on scope.
- Sold through Carahsoft for U.S. government procurement channels
- Funded by grants (UNDP MPTF, bilateral donors, foundations) + commercial licensing revenue

**API details:**
- REST API with cookie or OAuth authentication
- Filters: location (country, admin1, admin2), event type, actor, date range
- Rate limits on free tier; commercial license unlocks higher throughput
- Python package (`acled` on PyPI) and R package (`acledR`) available

**Target customers:**
- Academics and researchers (free tier)
- NGOs, UN agencies, humanitarian organizations
- Governments (via Carahsoft)
- Risk advisory firms (Verisk Maplecroft, Control Risks use ACLED as input)
- Media organizations
- Insurance, extractives, energy companies

**What Sentinel can learn:**
- ACLED's codebook and methodology are gold-standard -- Sentinel already uses ACLED as a core input
- CAST's approach (LightGBM + conformal inference) is directly comparable to Sentinel's XGBoost pipeline
- Their Early Warning Dashboard consolidation (4 tools behind one login) is good UX precedent
- Carahsoft distribution channel for government sales is worth noting

**Gaps Sentinel could fill:**
- ACLED operates at Admin1 granularity for forecasts -- Sentinel is at H3 hex-6 (~36 km2), roughly 70x finer
- ACLED's temporal grain is weekly data, monthly forecasts -- Sentinel targets daily with 72h lookahead
- No civilian-facing product -- ACLED is a researcher/analyst tool
- No evacuation routing or shelter awareness
- No real-time alerts (ACLED data has ~1 week lag)
- CAST doesn't fuse satellite, weather, or GDELT -- it's ACLED-only features

---

## 3. Crisis24 (GardaWorld)

**What it is:** The intelligence and risk management division of GardaWorld (Canadian private security conglomerate, ~$8B revenue). Formerly known as WorldAware/iJET. Provides travel risk management, critical event monitoring, crisis response, and executive protection.

**Data sources:**
- 200+ regularly updated country risk assessment reports (partnership with IHS Markit/S&P Global for country risk analysis)
- Integration with Dataminr for real-time social media/news event detection
- Proprietary analyst network: 24/7 global security operations center
- Open source intelligence (OSINT) aggregation
- Client-reported incidents
- Partnership with Palantir (Foundry) for data integration

**Products:**
1. **Crisis24 Dashboard:** Real-time global threat monitoring map, country risk reports, travel alerts
2. **Crisis24 AiiA Powered by Palantir (launched Oct 2025):** AI-driven anticipatory intelligence platform for C-suite. Modeled on head-of-state intelligence briefings (ICD 203 & 206 standards). Flagship output: "President's Brief" -- distills internal + external data streams into concise actionable insights.
3. **Mass notification:** Employee communication during crises
4. **Travel risk management:** Pre-trip risk assessments, traveler tracking
5. **Crisis response consulting:** On-call crisis management teams
6. **Executive/close protection services**

**Revenue model:**
- Enterprise SaaS subscriptions (annual contracts)
- Pricing: NOT public. Estimated $50K-$500K+/year for enterprise platform access depending on employee count and services
- Bundled with GardaWorld physical security services for upsell
- AiiA Powered by Palantir likely priced at premium tier ($100K+/year)
- Consulting fees for crisis response engagements

**Target customers:**
- Fortune 500 corporations (primary)
- Financial institutions (HSBC mentioned)
- Universities (Notre Dame mentioned for study abroad)
- Government agencies
- Energy/extractives companies operating in high-risk regions

**What Sentinel can learn:**
- The AiiA/Palantir partnership is a template for "intelligence briefing as a product" -- Sentinel's Gemini-powered alert narratives are a lightweight version of this
- Bundling risk data with actionable services (evac, shelter, routing) dramatically increases value vs. raw data
- ICD 203/206 compliance framing gives credibility with government buyers
- Mass notification is a natural adjacent feature for Sentinel

**Gaps Sentinel could fill:**
- Crisis24 operates at country/city level -- no hex-level granularity
- Priced out of reach for NGOs, local organizations, and civilians
- No public-facing product -- entirely behind enterprise paywall
- Prediction is "anticipatory intelligence" (analyst-driven) not ML-based probabilistic forecasting
- No open methodology -- black box to customers

---

## 4. International SOS

**What it is:** World's largest medical and security assistance company. Founded 1985. 12,000+ employees across 1,000+ locations in 90+ countries. Provides duty-of-care services for organizations with traveling/expatriate employees.

**Data sources:**
- Proprietary medical risk algorithm using 20+ internal and external data points
- In-house medical professionals worldwide providing ground-truth assessments
- Security risk ratings based on: criminal activity, political violence (terrorism, insurgency, war), social unrest, violent/petty crime
- Coverage: ~1,000 cities with detailed risk factors (conflict, crime, infrastructure, natural disasters, healthcare, health threats, air pollution)
- Partner data from Control Risks (security) and other intelligence providers

**Products:**
1. **Risk Map (annual):** Interactive global map with medical and security risk ratings (5-tier scale). Released annually with mid-year updates.
2. **Travel Risk Management platform:** Pre-trip advisories, real-time alerts, traveler tracking
3. **Medical assistance:** 24/7 phone consultations, clinic referrals, medical evacuations
4. **Security assistance:** Evacuation, extraction, crisis management
5. **Workforce Resilience:** Mental health, pandemic response
6. **Risk Outlook (annual report):** Published insights on emerging risks

**Revenue model:**
- Annual membership/subscription per organization
- Pricing: NOT public. Structured as per-employee-per-year. Industry estimates range from $5-$50+ per employee per year depending on risk profile and services, with enterprise contracts in the $100K-$1M+ range for large organizations
- Medical evacuation and assistance billed additionally in some plans
- 9,000+ client organizations including majority of Fortune Global 500

**Target customers:**
- Multinational corporations
- Governments (diplomatic corps, military families)
- Educational institutions (study abroad)
- NGOs and international organizations
- Energy, mining, construction companies

**What Sentinel can learn:**
- The annual Risk Map release is a marketing event that generates massive press coverage -- Sentinel could do quarterly "Levant Risk Reports" for visibility
- Medical + security risk layering is powerful -- Sentinel could layer health/infrastructure data onto conflict risk
- Per-employee pricing model for B2B is proven and scalable
- Integration with travel booking systems (Concur, Amadeus) is a distribution channel

**Gaps Sentinel could fill:**
- Country/city level only -- no sub-city granularity
- Annual/quarterly updates with limited real-time capability
- No ML-based forecasting -- analyst-driven ratings
- Zero civilian focus -- entirely corporate duty-of-care
- No open data or API for researchers

---

## 5. Riskline

**What it is:** Copenhagen-based travel risk intelligence company. Provides verified, independent risk assessments for 220+ countries/territories and 260+ cities. Focused specifically on the corporate travel management ecosystem.

**Data sources:**
- AI-powered processing of 1M+ sources (news, government sites, embassies, breaking news feeds)
- Global analyst network for verification and contextual analysis
- Real-time monitoring with automated alert generation
- 5-tier risk ranking system covering: political tensions, terrorism, conflicts, crime, natural disasters, health

**Products:**
1. **Risk Manager Platform:** Dashboard for corporate travel managers
2. **Travel Advisories API:** Structured risk data delivered via REST API
3. **Entry Requirements API:** Visa, vaccination, COVID requirements
4. **Incident Alerts:** Real-time push notifications
5. **City/Country Reports:** Detailed risk assessments

**Revenue model:**
- B2B SaaS: API licensing to travel management companies and travel tech platforms
- Pricing: NOT public. Likely per-API-call or per-user-per-month for enterprise
- Revenue driven primarily through partnerships/integrations rather than direct sales

**Key integration partners:**
- TripStax (TMC platform)
- Osprey Flight Solutions (aviation risk)
- Travelogix (travel data analytics)
- Safeture (employee safety, 4,000+ companies)
- A3M Global Monitoring
- Amadeus/Cytric (travel booking)

**Target customers:**
- Travel Management Companies (TMCs) -- primary
- Corporate travel departments
- Airlines and aviation operators
- Insurance companies
- Embassies and government travel offices

**What Sentinel can learn:**
- API-first distribution: Riskline's business is built on being embedded in OTHER platforms, not on its own dashboard
- The partner ecosystem approach (TMCs, booking systems, safety platforms) multiplies reach without direct sales
- Structured, standardized API output (JSON with consistent schema) enables easy integration
- Entry requirements data bundled with risk data increases stickiness

**Gaps Sentinel could fill:**
- Country/city level only -- no neighborhood or hex-level granularity
- No conflict prediction -- reactive risk ratings only
- No civilian use case -- entirely B2B corporate travel
- No evacuation routing or shelter data
- Focused on travel, not on people living in conflict zones

---

## 6. Global Conflict Tracker (CFR)

**What it is:** Free, public interactive tool from the Council on Foreign Relations' Center for Preventive Action (CPA). Tracks ~30 ongoing conflicts with assessments of status and U.S. policy implications.

**Data sources:**
- Expert judgment: government officials, foreign policy experts, academics (via annual Preventive Priorities Survey)
- CPA internal monitoring of conflict developments
- Watch lists, conflict assessments, government reports from other organizations
- Consultation with CFR subject-matter experts
- Monthly assessment cycle (or event-driven updates)

**Products:**
- Interactive conflict map (free, public)
- Annual Preventive Priorities Survey
- "Conflicts to Watch" annual report
- Background briefings on each conflict

**Revenue model:**
- FREE. Funded by CFR (nonprofit) and the Sue & Edgar Wachenheim Foundation
- No commercial product -- purely public education and policy influence
- CFR itself funded by membership dues ($10K+/year for corporate members), foundation grants, and government contracts

**Target customers:**
- U.S. policymakers (primary intended audience)
- Media and journalists
- Academics and students
- General public interested in foreign policy

**What Sentinel can learn:**
- Simple, clean UX: ~30 conflicts on a map with clear status indicators is digestible (vs. LiveUAMap's information overload)
- "Conflicts to Watch" framing generates annual media coverage
- Expert survey methodology adds credibility beyond pure ML
- Free public tools build brand authority that enables monetization elsewhere

**Gaps Sentinel could fill:**
- Only ~30 conflicts -- misses many sub-national situations
- Country level, no sub-national granularity
- Monthly or slower update cycle
- No data API, no structured data export
- Qualitative assessments only -- no quantitative risk scores
- No civilian utility (no alerts, routing, shelters)

---

## 7. ACLED (Full Organization Analysis)

*(Extends Section 2 above with organizational context)*

**Organizational structure:**
- Registered as a US 501(c)(3) nonprofit
- ~100+ researchers/coders globally
- Funded by mix of grants and commercial licensing
- UNDP Multi-Partner Trust Fund supports core operations
- Academic leadership (Clionadh Raleigh, University of Sussex)

**Data methodology:**
- Standardized codebook: 6 event types (battles, explosions/remote violence, violence against civilians, protests, riots, strategic developments)
- 25 sub-event types
- Actor coding: named groups, state forces, identity militias, etc.
- Fatality estimates (reported, often underestimates)
- Geographic precision codes (1=exact, 2=near, 3=ADM2 centroid)
- Source triangulation: events must appear in 2+ sources or from a highly reliable single source

**Scale:**
- 1M+ events coded (cumulative)
- ~200K new events coded annually
- Coverage back to 1997 for Africa, expanding globally since 2018

**Competitive position:**
- De facto standard dataset for conflict research
- Used as input by: ViEWS, CAST, Verisk Maplecroft, Control Risks, World Bank, UN agencies
- Main competitor: UCDP (different methodology, lower event count, stricter inclusion criteria)

**What Sentinel can learn:**
- ACLED's moat is its codebook and coding methodology -- consistency over time enables time-series analysis
- The shift from pure academic to commercial licensing is a model Sentinel could follow
- Carahsoft reseller relationship for government sales reduces go-to-market friction
- ACLED's geographic precision codes are an honest acknowledgment of data quality -- Sentinel should adopt similar

**Gaps Sentinel could fill:**
- ACLED is a dataset, not a decision tool
- ~1 week data lag makes it unsuitable for real-time civilian alerts
- No evacuation or response layer
- Commercial pricing excludes many NGOs and local organizations in conflict zones
- CAST forecasts don't fuse non-ACLED data sources

---

## 8. Uppsala Conflict Data Program (UCDP)

**What it is:** World's oldest running data collection project on organized violence (est. 1946 at Uppsala University, Sweden). The academic gold standard for armed conflict data.

**Data sources:**
- Coded from: news agencies, NGO reports, government documents, academic sources
- Stricter inclusion criteria than ACLED: requires 25+ battle-related deaths per year for "armed conflict" classification
- All sources are public/open

**Products & tools:**
1. **UCDP Conflict Encyclopedia:** Interactive web database with maps, charts, timelines. Free.
2. **Downloadable datasets:** Georeferenced Event Dataset (GED), Battle-Related Deaths, One-Sided Violence, Non-State Conflict, Peace Agreements. All free (CSV, Excel).
3. **Charts and maps:** Pre-made visualizations updated annually. Free download.
4. **R package (conflictr):** Tools for acquiring, processing, visualizing UCDP data.
5. **Our World in Data integration:** UCDP/PRIO data powers the War & Peace section.

**Revenue model:**
- FREE. Entirely grant-funded (Swedish Research Council, ERC grants)
- No commercial product
- Academic publications in Journal of Peace Research are the primary "output"

**Relationship to ViEWS:**
- UCDP and PRIO jointly run the ViEWS forecasting system (the academic SOTA)
- ViEWS uses UCDP data as ground truth for training/evaluation
- Available through Demscore platform alongside other democracy/governance datasets

**Target customers:**
- Academic researchers (primary)
- Policy organizations (UN, World Bank)
- Journalists covering conflict
- Other data projects (ViEWS, ACLED uses UCDP for validation)

**What Sentinel can learn:**
- UCDP's strict 25-death threshold creates a clean, high-confidence dataset -- useful for model validation even if too conservative for early warning
- The Journal of Peace Research publication pipeline gives academic credibility that unlocks grants
- Demscore aggregation (multiple datasets in one platform) is a model for data consolidation
- Free, open data built a massive ecosystem -- every conflict researcher uses UCDP

**Gaps Sentinel could fill:**
- Annual updates only (GED updated yearly) -- unusable for real-time
- Higher threshold misses low-level violence that civilians experience daily
- No forecasting product (ViEWS is separate)
- No civilian-facing tools
- Global scope means shallow depth in any one theater

---

## 9. HDX (Humanitarian Data Exchange) / ReliefWeb

**What it is:** HDX is OCHA's open data platform for humanitarian data. ReliefWeb is OCHA's editorial platform for humanitarian content. Both operated by the Centre for Humanitarian Data (The Hague).

**Data sources (HDX):**
- 20,000+ datasets from 1,500+ organizations
- 68% of datasets shared programmatically via APIs (automated ingestion)
- Sources include: UN agencies, NGOs (MSF, IRC, ICRC), governments, academic institutions
- Data types: population statistics, displacement figures, food security (IPC/CH), health, infrastructure, conflict events, administrative boundaries

**Products:**
1. **HDX Platform:** Search, filter, download datasets. Free. CKAN-based.
2. **HDX CKAN API:** General-purpose API for all datasets on the platform
3. **HDX HAPI (Humanitarian API):** Standardized access to curated humanitarian indicators across 25 countries. Single API for food security (IPC), food prices (WFP), sector presence, population, etc.
4. **ReliefWeb:** Editorial content -- situation reports, maps, infographics, job postings. ReliefWeb API available.
5. **HDX Tools:** Quick Charts, data validation, data-behind-the-grid views

**Revenue model:**
- FREE. Funded by OCHA (UN regular budget + donor contributions)
- No commercial product
- Mission is to reduce barriers to data access in humanitarian crises

**Target customers:**
- Humanitarian organizations (primary)
- Government aid agencies (USAID, DFID, etc.)
- Academic researchers
- Journalists
- Other data platforms that ingest HDX data

**What Sentinel can learn:**
- HDX HAPI is brilliant design: one API, standardized schema, multiple underlying sources. Sentinel's API should similarly abstract its data sources behind a clean interface.
- Automated data ingestion (68% programmatic) at scale is the right approach
- HDX's data validation pipeline catches quality issues before publishing
- The "data grid" concept (standardized indicators per country) makes cross-country comparison easy

**Gaps Sentinel could fill:**
- HDX aggregates but doesn't analyze -- no risk scoring, no prediction
- Data quality varies wildly across contributing organizations
- No real-time capability (most datasets updated weekly to monthly)
- No civilian-facing alerts or actionable guidance
- No geospatial resolution below admin level for most datasets

---

## 10. Premise Data

**What it is:** San Francisco-based (founded 2012, Series E) crowdsourced data collection platform. Pays gig workers globally to collect ground-level data via smartphone app.

**Data sources:**
- Crowdsourced: network of smartphone users paid $0.05-$0.10 per task
- Tasks: photograph store shelves, report prices, count ATMs, take geotagged photos, complete surveys
- Web scraping: crawls internet retailers for pricing data
- Ground-truth verification layer on top of other data sources

**Products:**
- Economic data: food prices, inflation tracking, market conditions
- Brand channel checks: retail presence, pricing compliance
- Infrastructure mapping: geotagged photos of facilities, roads, buildings
- Custom survey deployment to distributed workforce

**Revenue model:**
- B2B data licensing to governments, corporations, financial services
- Government/military contracts: at least $5M from U.S. Air Force and Army contracts since 2017
- Confirmed military/intelligence contracts in court filings (details classified)
- World Bank and humanitarian organization contracts for food price monitoring
- Hedge fund and financial services clients for alternative data

**Target customers:**
- Government/military/intelligence agencies
- World Bank, humanitarian organizations (food security monitoring)
- Financial services (hedge funds, commodity traders)
- Consumer goods companies (channel checks)
- Infrastructure planners

**What Sentinel can learn:**
- Crowdsourced ground-truth is a powerful complement to remote sensing and media monitoring
- Premise proved you can build a global data collection network with micro-payments ($0.05-$0.10 per task)
- The dual-use tension is real: Premise faced significant backlash when military contracts were revealed. Sentinel must be transparent about who can access what.
- Food price data (which Premise collects) is a proven leading indicator of conflict (NECSI Arab Spring prediction)

**Gaps Sentinel could fill:**
- Premise doesn't do conflict prediction -- it's a data collection tool
- No civilian-facing product
- Ground-truth collection in active conflict zones is extremely difficult/dangerous
- No real-time alert system
- Ethical concerns about using crowdworkers in conflict zones for intelligence purposes

---

## 11. Planet Labs / Maxar

### Planet Labs
**What it is:** San Francisco-based Earth observation company. Operates the largest constellation of imaging satellites (~200 Dove satellites). Provides daily global coverage at 3-5m resolution.

**Data sources:**
- Own satellite constellation: daily global imaging
- PlanetScope: 3-5m multispectral, daily revisit
- SkySat: 50cm resolution, video capability, tasked collection
- AI/ML analytics feeds: change detection, object classification, road/building detection

**Pricing:**
- Not publicly listed per-km2
- Subscription tiers based on area of interest and temporal frequency
- Tasking Dashboard uses pre-paid credits
- Subscriptions API free for users with download quotas
- Major contracts: $230M Asia-Pacific deal, 10-year NRO contract

### Maxar
**What it is:** Westminster, CO-based satellite imagery and geospatial intelligence company. Operates WorldView constellation. Highest-resolution commercial imagery available (30cm panchromatic).

**Data sources:**
- Own satellite constellation: WorldView-2, WorldView-3 (30cm), WorldView Legion
- 20+ year archive of high-resolution imagery
- AI-powered analytics: Maxar ARD (Analysis Ready Data), automated feature extraction
- $3.2 billion 10-year NRO contract

**Conflict monitoring use cases:**
- Ukraine: external researchers used Planet imagery to identify MLRS placements oriented toward Kharkiv
- Building damage assessment (before/after comparison)
- Refugee camp monitoring (tent counting, growth tracking)
- Infrastructure destruction verification
- Military vehicle/equipment detection and counting
- Maritime monitoring (vessel tracking in conflict zones)

**Revenue model (both):**
- Government/defense contracts (primary): NRO, NGA, DoD, allied governments
- Commercial subscriptions: insurance, agriculture, energy, mining
- Academic/research programs (discounted/free access for some use cases)
- Analytics-as-a-service: processed insights, not just raw imagery

**Target customers:**
- U.S. and allied defense/intelligence agencies (largest segment)
- Insurance companies (catastrophe assessment)
- Agriculture (crop monitoring)
- Energy/mining (site monitoring)
- Media (conflict/disaster verification)
- NGOs and humanitarian organizations (discounted programs)

**What Sentinel can learn:**
- Free Sentinel-1/2 data covers baseline monitoring; commercial tasking should be reserved for onset hexes (as noted in your existing research)
- PWTT method (AUC=0.88 for building damage from S1, one line of GEE code) means Sentinel doesn't NEED Planet/Maxar for damage assessment
- Planet paused public release of Middle East imagery during Iran conflict -- access restrictions during crises are a real risk for dependency
- AI analytics feeds (change detection, object classification) are the value-add, not raw imagery

**Gaps Sentinel could fill:**
- Planet/Maxar sell imagery, not conflict prediction
- No civilian-facing alerting
- Imagery alone doesn't tell you "what will happen tomorrow" -- it tells you what already happened
- No integration with ground-level data (ACLED events, GDELT, food prices)
- Cost prohibitive for civilian/NGO use at high resolution

---

## 12. Palantir

**What it is:** Denver-based data analytics company. $4.4B+ revenue (2025 guidance), ~$370B market cap. Three platforms: Gotham (defense/intel), Foundry (commercial), AIP (AI/LLM layer).

**Platforms:**
1. **Gotham:** "Operating System for Defense Decision Making." Integrates structured + unstructured data (databases, sensor feeds, reports, documents, images, communications). Used by CIA, FBI, NSA, U.S. military branches. Real-time geospatial mapping, network analysis, pattern detection.
2. **Foundry:** Commercial data integration and analytics. Ontology-based data modeling.
3. **AIP (Artificial Intelligence Platform):** LLM integration layer across Gotham and Foundry. Enables natural language queries over integrated data.

**Data sources:**
- Palantir doesn't own data -- it INTEGRATES customer data
- Ingests: databases, sensor feeds (SIGINT, IMINT, ELINT), reports, documents, satellite imagery, social media, communications intercepts
- The ontology layer maps relationships between entities across all data sources
- Customers bring their own data; Palantir provides the integration and analysis infrastructure

**Revenue model:**
- Multi-year subscription contracts
- Pricing: negotiated per deployment. Factors: number of use cases, data volume, users, customization level
- Forward Deployed Engineers (FDEs) work on-site to build ontology and train users -- high-touch, high-cost
- Government: 55% of revenue. $10B Army Enterprise Agreement (July 2025). $823M TITAN battlefield intelligence contract.
- Commercial: 45% of revenue, growing 121% YoY (Q3 2025). Average commercial deal expanding significantly.
- Enterprise Agreements consolidating multiple use cases into single high-value contracts

**Target customers:**
- U.S. and allied defense/intelligence agencies (primary)
- Law enforcement
- Fortune 500 corporations (supply chain, operations, fraud detection)
- Healthcare organizations
- Energy companies
- Financial institutions

**Crisis24 partnership:**
- Crisis24 AiiA Powered by Palantir (launched Oct 2025)
- Uses Palantir Foundry's ontology to integrate Crisis24's risk data
- Produces "President's Brief" style intelligence summaries for C-suite
- Built to ICD 203/206 intelligence community standards

**What Sentinel can learn:**
- Palantir's core insight: the hardest problem is DATA INTEGRATION, not any single algorithm. Sentinel's multi-source fusion (ACLED + GDELT + FIRMS + weather + Mapbox) is a miniature version of this.
- The ontology concept (mapping relationships between entities) could evolve Sentinel beyond hex-level scoring to entity-level tracking (which armed group, which supply route, which population center)
- FDE model is expensive but builds deep customer lock-in -- Sentinel could offer a lighter version (embedded analyst + platform access)
- AIP's natural language query layer is the future -- Sentinel's Gemini integration for alert narratives is a step in this direction

**Gaps Sentinel could fill:**
- Palantir is a platform, not a conflict-specific product. It requires massive customization per deployment.
- Costs $1M+ per year minimum -- inaccessible to NGOs, local governments, civilians
- No public-facing product whatsoever
- No civilian alerting, evacuation routing, or shelter awareness
- Palantir provides tools, not answers -- you still need analysts to interpret outputs
- No published methodology -- entirely opaque

---

## Comparative Matrix

| Platform | Granularity | Update Freq | Predictive? | Civilian Use | Pricing | Data Sources |
|----------|-------------|-------------|-------------|--------------|---------|--------------|
| LiveUAMap | Point events | Real-time | No | Yes (free) | Freemium | OSINT/social |
| ACLED Dashboard | Admin1 (forecast) | Weekly | Yes (CAST) | No | Free/commercial | Human-coded events |
| Crisis24 | Country/city | Real-time | Analyst-driven | No | Enterprise ($50K+) | IHS + Dataminr + analysts |
| International SOS | Country/city | Annual + alerts | No | No | Per-employee | Proprietary algo + analysts |
| Riskline | Country/city | Real-time | No | No | B2B API | 1M+ sources + analysts |
| CFR Tracker | Country | Monthly | No | Yes (free) | Free | Expert judgment |
| ACLED (full) | Event-level | Weekly | Yes (CAST) | No | Free/commercial | Human-coded events |
| UCDP | Event-level | Annual | No | No | Free | Human-coded events |
| HDX/ReliefWeb | Varies | Varies | No | No | Free | 1,500+ orgs |
| Premise | Point-level | Task-driven | No | No | B2B/gov | Crowdsourced |
| Planet/Maxar | 3-50cm pixels | Daily/tasked | No | No | Enterprise | Own satellites |
| Palantir | Configurable | Real-time | Configurable | No | $1M+/yr | Customer data |
| **Sentinel** | **H3 hex-6 (~36km2)** | **Daily/15min** | **Yes (XGBoost + tactical)** | **Yes (primary)** | **Free civilian** | **ACLED+GDELT+FIRMS+weather** |

---

## Key Takeaways for Sentinel

### 1. Nobody else targets civilians as the primary user
Every commercial platform targets enterprises, governments, or researchers. Sentinel's civilian-first approach is genuinely unique. This is both the opportunity and the challenge (civilians don't pay enterprise prices).

### 2. The resolution gap is real
ACLED CAST forecasts at Admin1. Crisis24/IntlSOS/Riskline at country/city. UCDP annually. Sentinel at H3 hex-6 daily is a genuine step change -- roughly 70x finer spatial resolution than the nearest forecasting competitor.

### 3. Integration is the moat, not any single data source
Palantir's $370B valuation is built on data integration, not data ownership. Sentinel's fusion of ACLED + GDELT + FIRMS + weather + Mapbox routing in a single scoring pipeline is the right approach. The question is expanding this (add Telegram, internet shutdowns, satellite embeddings).

### 4. Prediction is rare and valuable
Of the 12 platforms analyzed, only ACLED CAST does real ML-based conflict forecasting. LiveUAMap, Crisis24, IntlSOS, Riskline, CFR, UCDP, HDX, Premise, Planet/Maxar, and Palantir are all retrospective or analyst-judgment-based. Sentinel + ViEWS + CAST are essentially the only ML forecasting systems. This is a tiny competitive set.

### 5. Monetization patterns that work
- **Freemium data + enterprise analytics** (ACLED model): free basic access builds ecosystem, commercial license for corporate use
- **API-first distribution** (Riskline model): embed in partner platforms rather than building direct user base
- **Platform + services bundle** (Crisis24 model): data + consulting + physical response
- **Calibrated probability feeds** (insurance model): the highest-margin, most defensible product

### 6. Distribution channels to consider
- Carahsoft for U.S. government (ACLED's approach)
- Travel management platform APIs (Riskline's approach)
- Humanitarian API aggregation (HDX HAPI model)
- Direct-to-NGO (free tier builds relationships that convert to paid API access)

### 7. Critical risks from competitor landscape
- ACLED licensing at scale remains a dependency risk. If ACLED raises commercial prices or restricts access, Sentinel's core input is threatened.
- Planet/Maxar restricting Middle East imagery during conflicts shows that data access can be cut during the exact moments you need it most.
- Palantir + Crisis24 partnership (AiiA) could expand into conflict-specific forecasting, which would be a direct competitor with massive resources.

---

## Sources

- [LiveUAMap](https://liveuamap.com/) | [LiveUAMap Wikipedia](https://en.wikipedia.org/wiki/Liveuamap) | [LiveUAMap API](https://liveuamap.com/promo/api) | [Bellingcat Toolkit - LiveUAMap](https://bellingcat.gitbook.io/toolkit/more/all-tools/liveuamap)
- [ACLED](https://acleddata.com/) | [ACLED API Documentation](https://acleddata.com/acled-api-documentation) | [ACLED EULA](https://acleddata.com/eula) | [ACLED on Datarade](https://datarade.ai/data-providers/acled-data/profile) | [ACLED for Government via Carahsoft](https://www.carahsoft.com/acled-analysis)
- [Crisis24](https://crisis24.garda.com/) | [Crisis24 Risk Intelligence](https://www.crisis24.com/solutions/risk-intelligence-analysis) | [Crisis24 AiiA + Palantir](https://aiia.crisis24.com/) | [GardaWorld - Crisis24 AiiA Launch](https://www.gardaworld.com/news/crisis24-launches-crisis24-aiia-powered-by-palantir-delivering-state-level-intelligence-briefings-to-c-suite-and-board-leaders) | [Crisis24 Global Risk Forecast 2026](https://www.gardaworld.com/news/crisis24-global-risk-forecast-2026-future-ready-now)
- [International SOS Risk Outlook 2026](https://www.internationalsos.com/risk-outlook) | [International SOS Risk Map 2025](https://www.itij.com/latest/news/international-sos-has-released-its-annual-interactive-risk-map-2025) | [International SOS Membership](https://buymembership.internationalsos.com/compare/)
- [Riskline](https://riskline.com/) | [Riskline Technology Solutions](https://riskline.com/solutions/technology-solutions/) | [Riskline + TripStax](https://riskline.com/riskline-partners-with-tripstax-to-enhance-risk-management-support-for-tmcs/) | [Riskline + Osprey](https://www.ospreyflightsolutions.com/riskline-partners-with-osprey-flight-solutions-to-boost-risk-manager-platform)
- [CFR Global Conflict Tracker](https://www.cfr.org/global-conflict-tracker) | [CFR Methodology](https://www.cfr.org/global-conflict-tracker/methodology) | [CFR Conflicts to Watch 2026](https://www.cfr.org/reports/conflicts-watch-2026)
- [UCDP](https://www.uu.se/en/websites/ucdp---uppsala-conflict-data-program) | [UCDP Downloads](https://ucdp.uu.se/downloads/) | [UCDP/ViEWS on Demscore](https://www.demscore.se/partners/ucdpviews/)
- [HDX](https://data.humdata.org/) | [HDX Developer Resources](https://data.humdata.org/faqs/devs) | [HDX HAPI Announcement](https://centre.humdata.org/announcing-the-hdx-humanitarian-api/)
- [Premise Data](https://premise.com/) | [Premise Military Contracts (The Sun)](https://www.the-sun.com/news/3168062/premis-military-users-spies-without-knowing/) | [Premise Court Filing (Poulson)](https://jackpoulson.substack.com/p/premise-data-confirms-secret-military)
- [Planet Labs](https://www.planet.com/) | [Planet Defense & Intelligence](https://www.planet.com/industries/defense-and-intelligence/) | [Planet Pricing](https://www.planet.com/pricing/) | [NRO Contracts (SpaceNews)](https://spacenews.com/blacksky-maxar-planet-win-10-year-nro-contracts-for-satellite-imagery/)
- [Palantir Gotham](https://www.palantir.com/platforms/gotham/) | [Palantir Revenue Analysis (Visual Capitalist)](https://www.visualcapitalist.com/cp/where-does-palantirs-revenue-come-from/) | [Palantir Deep Dive (Seat11a)](https://seat11a.com/blog-palantir-technologies-a-deep-long-form-exploration-of-the-company/) | [Palantir 2026 Analysis](https://markets.financialcontent.com/stocks/article/finterra-2026-2-10-the-software-fortress-a-comprehensive-analysis-of-palantir-technologies-pltr-in-2026)
