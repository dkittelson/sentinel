# Sentinel — Complete Data Portfolio

**Compiled: 2026-03-26 | 6 research agents, 120+ sources audited**

This is the definitive inventory of every data source Sentinel can use, organized by integration priority. Each source is tagged as useful for **ONSET** (peaceful→violent), **CONTINUATION** (violent→more violent), or **BOTH**.

---

## CURRENTLY USING (5 sources)

| # | Source | Features | Signal |
|---|--------|----------|--------|
| 1 | ACLED events | event counts, fatalities, actor types | Both |
| 2 | GDELT events (basic) | event count, avg tone, Goldstein, hostility | Both |
| 3 | NASA FIRMS | fire detections (VIIRS/MODIS hotspots) | Continuation |
| 4 | Open-Meteo | temperature, precipitation, wind | Onset (slow) |
| 5 | Mapbox | routing, tiles, basemap | Infrastructure |

---

## TIER 1 — 2-WEEK SPRINT (free, high-signal, feasible)

### Conflict/Ground Truth
| # | Source | What | Access | Signal | Effort |
|---|--------|------|--------|--------|--------|
| 6 | **UCDP-GED** | Organized violence events, CC BY 4.0 | ucdp.uu.se/downloads, REST API | Both | 2 days |
| 7 | **Pikud HaOref (IDF sirens)** | Real-time rocket/missile alerts, JSON endpoint | oref.org.il/WarningMessages/alert/alerts.json | Both | 0.5 day |

### Text/NLP
| # | Source | What | Access | Signal | Effort |
|---|--------|------|--------|--------|--------|
| 8 | **GDELT GKG/GCAM expansion** | 2,230 emotional/thematic dimensions, Arabic filtering | data.gdeltproject.org GKG CSV | **Onset** | 2-3 days |
| 9 | **Telegram channels (Levant)** | Real-time conflict events, minutes ahead of GDELT | Telethon Python library, free | **Onset** | 2-3 days |

### Satellite/Remote Sensing
| # | Source | What | Access | Signal | Effort |
|---|--------|------|--------|--------|--------|
| 10 | **VIIRS Black Marble nightlights** | Daily 500m NTL, light drops = destruction/displacement | NASA Earthdata + `blackmarblepy` | Both | 1-2 days |
| 11 | **Sentinel-2 NDVI** | Vegetation change, burned areas, agricultural damage | CDSE Statistical API (free 10K PUs/mo) | Continuation | 1-2 days |

### Connectivity/Infrastructure
| # | Source | What | Access | Signal | Effort |
|---|--------|------|--------|--------|--------|
| 12 | **IODA internet outages** | BGP + active probing + darknet analysis | ioda.inetintel.cc.gatech.edu API | **Onset** | 1 day |
| 13 | **Cloudflare Radar** | Traffic anomalies for LB/SY/IL ASNs, ~20% of web traffic | developers.cloudflare.com/api (free token) | **Onset** | 1 day |

### Socioeconomic
| # | Source | What | Access | Signal | Effort |
|---|--------|------|--------|--------|--------|
| 14 | **FEWS NET/IPC food security** | IPC Phase 1-5, sub-national, Lebanon actively covered | ipcinfo.org API | **Onset** | 1 day |
| 15 | **WFP VAM food prices** | Weekly bread/fuel prices at market level, LB + SY | api.vam.wfp.org (free) | **Onset** | 1 day |
| 16 | **LBP black market exchange rate** | Real-time parallel rate, THE economic barometer for Lebanon | github.com/Murf-y/LBP-DollarRate-API | **Onset** | 0.5 day |
| 17 | **WorldPop population** | 100m gridded population for risk normalization | worldpop.org API + GEE | Both | 1 day |

### Military/OSINT
| # | Source | What | Access | Signal | Effort |
|---|--------|------|--------|--------|--------|
| 18 | **Google Trends (Hebrew mobilization)** | Search spikes for צו 8, מילואים, פיקוד העורף | pytrends library (free) | **Onset** | 0.5 day |
| 19 | **UNIFIL/UNDOF via ReliefWeb** | Blue Line border incidents, ceasefire violations | api.reliefweb.int (free, JSON) | **Onset** | 1 day |

### Maritime/Supply Chain Context
| # | Source | What | Access | Signal | Effort |
|---|--------|------|--------|--------|--------|
| 20 | **IMF PortWatch** | 2,033 ports + 28 chokepoints (incl. Suez), transit volumes, disruption alerts | portwatch.imf.org API (GeoServices, CSV, GeoJSON) free | Supply chain overlay | 1-2 days |
| 21 | **AIS vessel tracking (aisstream.io)** | Real-time coastal vessel positions for Beirut, Haifa, Suez, Red Sea coast | aisstream.io WebSocket (free, coastal ~200km) | Supply chain overlay | 1-2 days |

### Calendar/Context
| # | Source | What | Access | Signal | Effort |
|---|--------|------|--------|--------|--------|
| 22 | **Religious/cultural calendar** | Ramadan, Ashura, Jerusalem Day, Nakba Day, Yom Kippur | Hardcoded / Islamic calendar API | **Onset** (modulator) | 0.5 day |

**Tier 1 total: 17 new sources, ~18-23 days of work, all free**

**Note on maritime sources:** IMF PortWatch and aisstream.io are **context overlays** for the supply chain and insurance APIs, not ML model inputs. They help customers visualize shipping activity alongside conflict risk hexes. For open-ocean satellite AIS coverage, upgrade to Kpler/Datalastic ($80-1000+ EUR/mo) once a supply chain customer is paying.

---

## TIER 2 — MONTH 2-3 (high value, moderate effort)

### Conflict/Ground Truth
| # | Source | What | Access | Signal |
|---|--------|------|--------|--------|
| 21 | **Airwars** | Geolocated airstrike/drone data with civilian harm | airwars.org API (free) | Continuation |
| 22 | **B'Tselem** | Israeli-Palestinian violence incidents, geocoded | btselem.org (scraping) | Both |
| 23 | **UCDP Ceasefire Dataset** | Ceasefire status/violations | ucdp.uu.se/downloads (free) | **Onset** |
| 24 | **VIEWS forecasts** | Monthly sub-national conflict predictions, ensemble input | viewsforecasting.org REST API (free) | **Onset** |

### Text/NLP
| # | Source | What | Access | Signal |
|---|--------|------|--------|--------|
| 25 | **Arabic news RSS** | Al Jazeera, Al Mayadeen, An-Nahar, NNA | RSS feeds (free) | **Onset** |
| 26 | **Hebrew news RSS** | Ynet, Times of Israel, Jerusalem Post | RSS feeds (free) | **Onset** |
| 27 | **IDF Telegram channels** | Official operational announcements | Telethon (free) | Both |
| 28 | **ACLED notes NLP** | Weapon types, actor names, tactical detail from text field | XLM-R + PCA (compute only) | Both |
| 29 | **ReliefWeb API** | Humanitarian reports, escalation language extraction | api.reliefweb.int (free) | Continuation |

### Satellite/Remote Sensing
| # | Source | What | Access | Signal |
|---|--------|------|--------|--------|
| 30 | **GNSS/GPS interference** | Jamming/spoofing as military EW precursor | GPSJam.org / OpenSky ADS-B | **Onset** |
| 31 | **TROPOMI NO2/aerosol** | Atmospheric anomalies from bombing/fires | GEE or CDSE (free) | Continuation |
| 32 | **Dynamic World** | Real-time 10m land cover change (built-up→bare = destruction) | GEE (free) | Continuation |
| 33 | **NOTAMs airspace closures** | 24-48h leading indicator of military operations | FAA API / Notamify (free) | **Onset** |
| 34 | **OpenSky ADS-B** | Military ISR aircraft surges precede strikes | opensky-network.org Python API | **Onset** |
| 35 | **Microsoft Building Footprints** | 1.4B buildings, base layer for damage detection | Planetary Computer (free) | Both |
| 36 | **UNOSAT damage labels** | Building-level damage assessments for training/validation | data.humdata.org/organization/unosat | Both |

### Connectivity/Infrastructure
| # | Source | What | Access | Signal |
|---|--------|------|--------|--------|
| 37 | **BGPStream (pybgpstream)** | Real-time BGP monitoring for LB/SY/IL ASN prefixes | CAIDA (free Python library) | Both |
| 38 | **OONI censorship** | App/website blocking as repression indicator | ooni.org/data API (free) | **Onset** |
| 39 | **IOM DTM border crossings** | Displacement + border status at Admin-1/2 | dtm.iom.int API v3 (free) | Both |
| 40 | **Israeli GTFS-RT transit** | Northern route suspensions = 0-6h onset signal | hasadna/open-bus (free) | **Onset** |

### Socioeconomic
| # | Source | What | Access | Signal |
|---|--------|------|--------|--------|
| 41 | **OCHA FTS aid funding gaps** | Humanitarian funding shortfalls destabilize | api.hpc.tools (free) | **Onset** |
| 42 | **OFAC sanctions changes** | New Hezbollah/Iran designations = escalation | sanctionslist.ofac.treas.gov XML (free) | **Onset** |
| 43 | **UNHCR refugee flows** | Registration surges = cross-border violence | data.unhcr.org API (free) | Both |
| 44 | **Sub-national HDI** | Development gradient between adjacent hexes | globaldatalab.org (free) | **Onset** |
| 45 | **Google Trends (Arabic conflict terms)** | Search for ملجأ, إخلاء, حرب, مطار | pytrends (free) | **Onset** |

### Military/OSINT
| # | Source | What | Access | Signal |
|---|--------|------|--------|--------|
| 46 | **USNI Fleet Tracker** | US carrier strike group positions, eastern Med | news.usni.org (free, weekly scrape) | **Onset** |
| 47 | **Alma Center** | Mapped Hezbollah infrastructure, static layer | alma-center.org (free) | **Onset** |

---

## TIER 3 — POST-FUNDING (high effort or niche)

### Satellite
| # | Source | What | Access | Signal |
|---|--------|------|--------|--------|
| 48 | Sentinel-1 SAR damage (PWTT) | Building damage per hex via coherence loss | GEE commercial ($500/mo) or CDSE | Continuation |
| 49 | NISAR L-band SAR | Better penetration through smoke, free | ASF DAAC (maturing ecosystem) | Both |
| 50 | GHSL built-up area | Baseline pre-conflict built-up footprint | GEE (free) | Both |
| 51 | ESA WorldCover | 10m land cover baseline | GEE/AWS (free) | Both |
| 52 | DAHITI water levels | Reservoir/river anomalies (Litani, Sea of Galilee) | dahiti.dgfi.tum.de API (free) | Onset |
| 53 | MODIS snow cover | Golan/Hermon military constraint | NASA Earthdata (free) | Onset |
| 54 | CAMS GFAS smoke/fire | Smoke transport, emission intensity | CDS API (free) | Continuation |

### Text/NLP
| # | Source | What | Access | Signal |
|---|--------|------|--------|--------|
| 55 | Reddit r/lebanon, r/syriancivilwar | Sentiment, firsthand reports | PRAW free tier | Both |
| 56 | UNSC transcripts | Escalation language in debates | Zenodo / UN Digital Library | Onset (slow) |
| 57 | ICG CrisisWatch | Monthly escalated/de-escalated flags | crisisgroup.org (scraping) | Onset |
| 58 | SOHR daily casualties | Syrian Observatory daily reports | syriahr.com (scraping) | Continuation |

### Socioeconomic
| # | Source | What | Access | Signal |
|---|--------|------|--------|--------|
| 59 | WHO HeRAMS | Hospital functionality status | WHO partnership required | Both |
| 60 | School closures (South Lebanon) | 24-72h leading indicator | MoE scraping | **Onset** |
| 61 | Meta Data for Good | Population density + crisis movement maps | dataforgood.facebook.com (apply) | Both |
| 62 | INFORM Risk sub-indicators | Structural vulnerability decomposed | drmkc.jrc.ec.europa.eu (free) | Onset |
| 63 | V-Dem democracy indices | 531 governance indicators | v-dem.net (free) | Onset |
| 64 | EPR ethnic settlement patterns | Sectarian heterogeneity per hex | icr.ethz.ch GIS shapefiles | Onset |

### Infrastructure
| # | Source | What | Access | Signal |
|---|--------|------|--------|--------|
| 65 | Google/Mapbox traffic anomalies | Checkpoint detection, military convoys | Maps API (~$15-50/mo) | Both |
| 66 | Freightos Baltic Index | Shipping rate spikes = escalation | freightos.com (free tier) | Onset |
| 67 | ~~AIS vessel tracking~~ | **Promoted to Tier 1 (#21)** | — | — |
| 68 | Ookla Open Data | Network performance tiles at 600m | AWS Open Data (free, quarterly) | Continuation |
| 69 | OSM changeset monitoring | Building deletions = damage signal | Overpass API (free) | Continuation |
| 70 | Globalping | On-demand traceroutes to LB/SY targets | globalping.io API (free) | Continuation |

### Military
| # | Source | What | Access | Signal |
|---|--------|------|--------|--------|
| 71 | CFR Cyber Ops Tracker | State-sponsored cyber operations | cfr.org (free) | Onset |
| 72 | DSCA major arms sales | US weapons deliveries to region | dsca.mil (free, scrape) | Onset (slow) |
| 73 | EMSC felt reports | Crowdsourced shaking = possible explosions | emsc-csem.org API (free) | Continuation |
| 74 | ITIC weekly reports | Detailed Hezbollah/Hamas attack analysis | terrorism-info.org.il (scraping) | Both |

---

## SKIP (dead, paid, or low signal-to-effort)

| Source | Reason |
|--------|--------|
| ACLED CAST | Paid, within ACLED commercial license |
| GTD (Global Terrorism Database) | Closed access since 2025 |
| REIGN | Archived 2021 |
| Polity V | Frozen 2018 (V-Dem is better) |
| Twitter/X API | $200+/month minimum |
| MarineTraffic API | Paid for historical |
| EventRegistry/NewsAPI free tier | Too limited for production |
| Bluesky/Mastodon/Threads | Insufficient Levant OSINT community |
| WhatsApp/Signal monitoring | Ethical/legal barriers |
| Uber/ride-hailing data | No API available |
| Food delivery app data | No API available |
| Satellite phone data | Not publicly available |
| Acoustic monitoring | No datasets exist |
| CTBTO seismic | Restricted to national data centers |
| RF monitoring (Unseenlabs etc.) | Commercial/classified only |
| SMAP soil moisture | 36km resolution, no conflict application |
| GRACE gravity | 300km monthly, wrong scale |
| Drone swarm detection | No satellite capability exists |
| Cryptocurrency analysis | Too expensive, low signal |
| Apple Mobility Trends | Ended 2022 |
| Google Community Mobility | Ended 2022 |
| SCAD | Doesn't cover Levant |
| Correlates of War MID | Multi-year lag |

---

## FEATURE COUNT SUMMARY

| Stage | Sources | Approx Features | Status |
|-------|---------|-----------------|--------|
| Current (v1) | 5 | ~52 | Live |
| After 2-week sprint (v2) | 22 | ~120-150 + maritime overlays | Target |
| After Month 2-3 (v3) | 49 | ~200-250 | Post-funding |
| Full portfolio (v4) | 76 | ~300+ | Long-term |

---

## THE ONSET FEATURE SET (what matters most)

These are the sources that specifically predict violence in peaceful areas — the hardest and most valuable prediction:

**Leading indicators (hours to days):**
1. GDELT GKG emotional indicators (fear/anger spikes in Arabic media)
2. IODA internet outages (shutdowns precede military action)
3. Cloudflare Radar traffic anomalies
4. Pikud HaOref siren escalation curves (0→5 sirens/day = escalation)
5. NOTAMs airspace closures (24-48h before strikes)
6. Google Trends Hebrew mobilization terms (צו 8)
7. GPS/GNSS jamming intensity (EW activates before kinetic)
8. OpenSky military ISR aircraft surges
9. IDF Telegram "enhanced readiness" announcements
10. Israeli GTFS-RT northern transit suspensions
11. Telegram Levant channel volume spikes

**Structural indicators (weeks to months):**
12. FEWS NET/IPC food security phase transitions
13. WFP food price spikes (bread, fuel)
14. LBP black market currency crash
15. UNIFIL Blue Line violation frequency
16. OCHA aid funding gap widening
17. OFAC new sanctions designations
18. UNHCR registration surges at borders
19. Sub-national HDI gradient between hexes
20. UCDP ceasefire status (holding→strained→collapsed)

**Modulators (affect timing, not cause):**
21. Religious calendar (Ramadan, Jerusalem Day, Nakba Day)
22. Election windows (90 days before/after)
23. Weather extremes (heat waves, drought via SPEI)
24. MODIS snow cover (Golan/Hermon seasonal constraint)
