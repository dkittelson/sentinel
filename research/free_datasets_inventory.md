# Free Datasets Inventory for Sentinel

## Priority Tier 1 — Integrate ASAP (highest ROI)

### 1. VIIRS Nighttime Lights / NASA Black Marble
- **URL:** blackmarble.gsfc.nasa.gov
- **API:** NASA LAADS DAAC (free Earthdata login); Python package `blackmarblepy` (World Bank)
- **Data:** Daily nighttime light composites at 500m, 2012-present (VNP46A2)
- **License:** Free (NASA open data)
- **Value:** Strongest satellite conflict indicator. Light drops = infrastructure destruction, power failure, displacement.

### 2. Telegram Public Channels (OSINT)
- **Tools:** Telethon (Python), Statiko (free unlimited monitoring incl. edit/deletion tracking)
- **Data:** Real-time conflict events from Lebanese news, Hezbollah-affiliated, IDF alert channels
- **License:** Free (Telegram API)
- **Value:** Minutes-to-hours lead time over GDELT. Primary info source in Levant conflict zones.

### 3. UCDP-GED + Candidate Events
- **URL:** ucdp.uu.se/downloads/ | API: ucdp.uu.se/apidocs/
- **Data:** Individual organized violence events globally (1989-2024), geo-coded, daily precision. Candidate Events = near-real-time.
- **License:** CC BY 4.0 — fully free
- **Value:** Direct ACLED replacement. No commercial license risk. Stricter coding (organized violence only).

### 4. IODA Internet Outages
- **URL:** ioda.inetintel.cc.gatech.edu
- **API:** Free, near-real-time + historical, country + sub-national + AS level
- **Data:** BGP routing + active probing + darknet traffic analysis
- **License:** Free (Georgia Tech)
- **Value:** Internet shutdowns preceded military action in Myanmar, Sudan, Tigray. Lowest FPR leading indicator.

### 5. FEWS NET / IPC Food Security
- **URL:** fews.net + ipcinfo.org
- **Data:** IPC Phase 1-5 at sub-national level. Lebanon actively covered (Baalbek-El Hermel at Crisis Phase 3 through Sept 2026).
- **License:** Free
- **Value:** Food insecurity is one of the strongest conflict escalation predictors.

### 6. GDELT GKG Expansion (features you're missing)
- **GCAM suite:** 2,200+ emotions/themes. Extract fear/anger/anxiety spikes in Arabic-language coverage.
- **GKG GeoJSON API:** `api.gdeltproject.org/api/v2/geo/geo` — live maps by theme
- **Arabic/Hebrew/French filtering** — are you using all 65 languages?
- **Entity extraction:** persons, organizations, co-occurrence networks

## Priority Tier 2 — High value, more effort

### 7. Sentinel-1 SAR Damage Detection
- **URL:** dataspace.copernicus.eu (10,000 free PUs/month)
- **Tools:** PWTT (AUC=0.88), open-source war destruction tool (Nature 2025)
- **Value:** Automated building damage per hex. Proven for Gaza, Ukraine, Syria.

### 8. WorldPop Population
- **URL:** worldpop.org | API + Google Earth Engine
- **Data:** 100m gridded population estimates, 242 countries, 2015-2030, age/sex disaggregation
- **License:** Free
- **Value:** Normalize risk scores by population. A hex with 50K people at moderate risk > a hex with 100 people at high risk.

### 9. IOM DTM Displacement
- **URL:** dtm.iom.int | API v3 (free registration)
- **Data:** Sub-national displacement at Admin-1/2. Active Syria coverage (March 2026).
- **License:** Free (registration)
- **Value:** Displacement flows predict cascade effects. Maps to H3 hexes.

### 10. VIEWS Forecasts (Ensemble Input)
- **URL:** viewsforecasting.org | Free REST API
- **Data:** Monthly forecasts 1-36 months ahead. Sub-national for Middle East at 0.5° grid.
- **License:** Free
- **Value:** Use as ensemble feature or benchmark. Maps to H3 hexes.

### 11. SPEI Global Drought Index
- **URL:** spei.csic.es
- **Data:** Multi-timescale drought severity (1-48 months), global, 0.5°, 1901-present
- **License:** Free
- **Value:** Drought is a proven conflict driver in the Middle East. Single standardized value per hex per month.

### 12. Microsoft Global Building Footprints
- **URL:** github.com/microsoft/GlobalMLBuildingFootprints
- **Data:** 1.4B buildings globally. Lebanon + Syria covered. Updated Feb 2026.
- **License:** CDLA Permissive 2.0 (free, commercial OK)
- **Value:** Base layer for SAR damage detection. Building count = population proxy.

## Priority Tier 3 — Useful context

### 13. OpenStreetMap (via Overpass API)
- Roads, hospitals, schools, shelters, checkpoints, refugee camps per hex
- Syria: ~173,400 km mapped roads
- Essential for evacuation routing

### 14. OONI Internet Censorship
- **URL:** ooni.org/data/ | Free REST API, near-real-time
- Censorship escalation (blocking news/messaging apps) precedes conflict

### 15. FAO Food Prices
- **URL:** fao.org/faostat/ | GIEWS FPMA tool
- Sub-national consumer prices for staple foods. Bread price spike in Tripoli = leading indicator.

### 16. UNHCR Refugee Data
- **URL:** api.unhcr.org — free, no credentials
- 70 years of displacement data. Syrian refugee concentrations in Bekaa Valley.

### 17. Global Fishing Watch
- **URL:** globalfishingwatch.org/our-apis/ | Python client (April 2025)
- Naval blockade patterns, unusual vessel concentrations off Lebanese coast
- Free for non-commercial use

### 18. OpenSky Flight Data
- **URL:** opensky-network.org | Free REST API (8,000 credits/day for contributors)
- Military aviation patterns, airspace closures, civilian flight diversions

### 19. EPR Ethnic Settlement Patterns
- **URL:** icr.ethz.ch/data/epr/ | GIS shapefiles
- Ethnic group settlement patterns for Lebanon/Syria → ethnic heterogeneity index per hex

### 20. V-Dem Democracy Indices
- **URL:** v-dem.net/data/ | R package `vdemdata`
- 531 indicators. Annual, country-level. Useful for structural risk baseline.

### 21. Sentinel-2 Optical
- Via CDSE (free). NDVI drops, burn scars, destroyed infrastructure.

## Skip These
- **GTD** — closed access as of 2025
- **SCAD** — doesn't cover Levant, not updated
- **REIGN** — archived 2021
- **Polity V** — frozen 2018 (V-Dem is better)
- **Twitter/X API** — paid only ($200+/month)
- **MarineTraffic** — paid API
- **EventRegistry/NewsAPI** — free tier too limited for production

## Additional Resources
- **HDX (data.humdata.org)** — meta-source aggregating ACLED, UNOSAT, OSM, displacement, food security. Single API for multiple datasets.
- **ReliefWeb API** — curated humanitarian reports, NLP-ready
- **UNOSAT Damage Assessments** — expert-annotated building damage (Gaza, Ukraine, Syria). Best training/validation data for SAR models.
- **Copernicus Emergency Management Service** — historical satellite damage maps for Levant conflicts
- **SIPRI Arms Transfers** — annual, too slow for tactical prediction
- **ERA5 Reanalysis** — upgrade from Open-Meteo (more variables, longer history)
- **CHIRPS Rainfall** — 5km resolution, better than Open-Meteo for drought detection
