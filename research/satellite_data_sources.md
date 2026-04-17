# Satellite Data Sources Research for Sentinel

**Date:** 2026-03-26
**Purpose:** Comprehensive inventory of free/open satellite data sources and platforms for conflict prediction in the Levant (Lebanon, N. Israel, S. Syria) at H3 hex-6 resolution (~36 km^2).

---

## Table of Contents
1. [Google Earth Engine (GEE)](#1-google-earth-engine-gee)
2. [NASA Earthdata / LANCE NRT](#2-nasa-earthdata--lance-nrt)
3. [ESA Copernicus Beyond Sentinel Hub](#3-esa-copernicus-beyond-sentinel-hub)
4. [UNOSAT / UNITAR Damage Assessments](#4-unosat--unitar-damage-assessments)
5. [Microsoft Planetary Computer](#5-microsoft-planetary-computer)
6. [AWS Open Data / Google Public Datasets](#6-aws-open-data--google-public-datasets)
7. [OpenAerialMap](#7-openaerialmap)
8. [Pre-Processed Satellite-Derived Datasets](#8-pre-processed-satellite-derived-datasets)
9. [Synthetic Aperture Radar (SAR)](#9-synthetic-aperture-radar-sar)
10. [Conflict-Specific Satellite Analysis Tools](#10-conflict-specific-satellite-analysis-tools)
11. [Air Quality / Atmospheric as Conflict Indicators](#11-air-quality--atmospheric-as-conflict-indicators)
12. [Other Platforms and Datasets](#12-other-platforms-and-datasets)
13. [Priority Matrix: What to Integrate When](#13-priority-matrix-what-to-integrate-when)

---

## 1. Google Earth Engine (GEE)

### What It Is
Google Earth Engine is a cloud-based geospatial analysis platform that combines a multi-petabyte catalog of satellite imagery and geospatial datasets with planetary-scale compute. You write analysis code (Python or JavaScript), and GEE runs it on Google's infrastructure -- no need to download terabytes of imagery to your own machine.

### How It Works
- You define an area of interest (AOI), a date range, and a dataset (e.g., Sentinel-1 GRD).
- GEE lazily loads only the tiles you need and runs your analysis server-side.
- Results (images, statistics, time series) can be exported to Google Drive, Cloud Storage, or returned inline.
- The Python API (`earthengine-api` / `ee` library) is the primary way to integrate with a backend like FastAPI.

### Is It Free?
**Yes, with caveats depending on use case:**

| Tier | Monthly Quota | Notes |
|------|--------------|-------|
| Community (default) | 150 EECU-hours | Free for noncommercial use. Soft limit -- degrades to "restricted mode" when exceeded, not a hard cutoff. |
| Contributor | 1,000 EECU-hours | Must apply; for higher-impact noncommercial work. |
| Partner | Higher | For major research orgs. |
| Commercial | $500/mo base | $1.33/hr online EECU, $0.40/hr batch EECU. Google for Startups Cloud Program offers up to $100K/yr in credits. |

**Starting April 27, 2026**, all noncommercial projects must select a tier (defaults to Community). The quota is measured in EECU-hours (Earth Engine Compute Unit hours). A typical Sentinel-1 zonal stats computation over the Levant would use a fraction of 1 EECU-hour.

**For Sentinel the startup:** Start on the Community tier (free, 150 EECU-hours/mo). If you get into the Google for Startups program, you get $100K cloud credits which covers commercial GEE too.

### Conflict-Relevant Datasets Available Through GEE

| Dataset | GEE Collection ID | Resolution | Cadence | Relevance |
|---------|-------------------|------------|---------|-----------|
| Sentinel-1 SAR GRD | `COPERNICUS/S1_GRD` | 10m | 6 days | Building damage detection (PWTT), coherence change |
| Sentinel-2 L2A | `COPERNICUS/S2_SR_HARMONIZED` | 10m | 5 days | NDVI cropland damage, urban change, burn scars |
| VIIRS Nighttime Lights (VNP46A2) | `NASA/VIIRS/002/VNP46A2` | 500m | Daily | Power outages, infrastructure destruction, population displacement |
| Sentinel-5P TROPOMI NO2 | `COPERNICUS/S5P/OFFL/L3_NO2` | 5.5km | Daily | Bombing/shelling indicators via atmospheric anomalies |
| Sentinel-5P TROPOMI Aerosol Index | `COPERNICUS/S5P/OFFL/L3_AER_AI` | 5.5km | Daily | Fire/destruction smoke plumes |
| Sentinel-5P TROPOMI SO2 | `COPERNICUS/S5P/OFFL/L3_SO2` | 5.5km | Daily | Fuel depot destruction, industrial damage |
| Sentinel-5P TROPOMI CO | `COPERNICUS/S5P/OFFL/L3_CO` | 5.5km | Daily | Sustained combustion from infrastructure fires |
| Dynamic World | `GOOGLE/DYNAMICWORLD/V1` | 10m | ~5 days | Real-time land use change (buildings, cropland, bare ground transitions) |
| GHSL Built-Up Surface | `JRC/GHSL/P2023A/GHS_BUILT_S` | 10m | Epoch (2018, 2020, etc.) | Baseline built-up area for pre/post damage comparison |
| ESA WorldCover | `ESA/WorldCover/v200` | 10m | Annual (2021) | Baseline land cover classification |
| ERA5 Daily Climate | `ECMWF/ERA5_DAILY` | ~31km | Daily | Weather features (already using Open-Meteo, but ERA5 is more comprehensive) |
| DMSP-OLS Nighttime Lights | `NOAA/DMSP-OLS/NIGHTTIME_LIGHTS` | ~1km | Annual (1992-2014) | Historical baseline of nighttime lights pre-VIIRS |
| MODIS NDVI | `MODIS/061/MOD13A2` | 1km | 16-day | Vegetation health / agricultural damage at broader scale |
| SRTM DEM | `USGS/SRTMGL1_003` | 30m | Static | Terrain features (elevation, slope) for tactical scoring |
| ALOS PALSAR Mosaic | `JAXA/ALOS/PALSAR/YEARLY/SAR` | 25m | Annual | L-band SAR baseline for forest/vegetation penetration |
| CAMS NRT Air Quality | `ECMWF/CAMS/NRT` | ~40km | Daily | Modeled air quality (PM2.5, PM10, O3, NO2) |

### Can You Run PWTT on GEE?
**Yes.** The PWTT (Pixel-Wise T-Test) algorithm by Ollie Ballinger is designed to run on Sentinel-1 GRD imagery, which is available in GEE. The workflow:
1. Load pre-conflict and post-conflict Sentinel-1 image stacks for the AOI
2. Compute pixel-wise mean and standard deviation for each stack
3. Run a two-sample t-test per pixel
4. Threshold the t-statistic to classify damage

The Nature 2025 paper (ETH Zurich / prs-eth/ukraine-damage-mapping-tool) explicitly runs its damage mapping tool on GEE and is MIT-licensed.

### Can You Compute Per-Hex Statistics?
**Yes.** GEE supports zonal statistics natively via `ee.Image.reduceRegions()`. The workflow:
1. Generate H3 hex-6 polygons for the Levant using `h3-py` (~2,000 hexes)
2. Upload them as a GEE FeatureCollection
3. Use `reduceRegions()` with reducers like `ee.Reducer.mean()`, `ee.Reducer.stdDev()`, etc.
4. Export the resulting table (hex_id + feature values) as CSV or to BigQuery

There is a dedicated tutorial on "Zonal Statistics With Google Earth Engine And H3 Hexagons" (ExpertBeacon). The World Bank also maintains `worldbank/GEE_Zonal`, a Python library specifically for this.

### Python API
```
pip install earthengine-api
```
- Library: `import ee`
- Auth: `ee.Authenticate()` (one-time), then `ee.Initialize(project='your-project')`
- Works in any Python environment (FastAPI backend, Jupyter, scheduled cron)
- Can export results to Google Drive or Cloud Storage for downstream ingestion into Supabase

### Verdict for Sentinel
**HIGH PRIORITY.** GEE is the single most impactful platform to integrate. It gives you:
- Free compute for SAR damage detection, nighttime lights, TROPOMI, and Dynamic World
- Per-hex zonal stats without downloading imagery
- A Python API that integrates with your FastAPI backend
- The ability to run the PWTT or ETH Zurich damage tool directly

**Integration effort: 1-2 week sprint** for a basic pipeline (Sentinel-1 SAR coherence + VIIRS nighttime lights + TROPOMI NO2 aggregated to H3 hexes).

---

## 2. NASA Earthdata / LANCE NRT

### Near-Real-Time Products

| Product | ID | Resolution | Latency | Access |
|---------|----|------------|---------|--------|
| VIIRS Active Fire (FIRMS) | VNP14IMGTDL_NRT | 375m | ~3 hours | Already using -- REST API |
| VIIRS Black Marble Nighttime Lights | VNP46A2 NRT | 500m (15 arc-sec) | ~3 hours | LANCE NRT download or GEE |
| VIIRS Surface Reflectance | VNP09_NRT | 375m-750m | ~3 hours | LANCE |
| MODIS Active Fire | MCD14DL | 1km | ~3 hours | FIRMS API |
| MODIS Aerosol Optical Depth | MOD04_L2 NRT | 10km | ~3 hours | LANCE |
| Sentinel-5P TROPOMI NO2 NRT | S5P_L2__NO2____HiR_NRT | 5.5km x 3.5km | ~3 hours | GES DISC / Earthdata |
| Sentinel-5P TROPOMI Aerosol NRT | S5P_L2__AER_AI_HiR_NRT | 5.5km x 3.5km | ~3 hours | GES DISC / Earthdata |

### VIIRS Black Marble Details
- **Product:** VNP46A2 (daily, gap-filled, BRDF-corrected nighttime lights)
- **Resolution:** 500m (15 arc-second grid)
- **Format:** HDF-EOS5 (HDF5)
- **7 Science Data Sets:** DNB BRDF-Corrected NTL, Gap-Filled DNB BRDF-Corrected NTL, DNB Lunar Irradiance, Latest High-Quality Retrieval, Mandatory Quality Flag, Cloud Mask Quality Flag, Snow Flag
- **Why it matters:** Daily nighttime light changes detect power outages, infrastructure destruction, and population displacement. A sudden drop in NTL radiance in a hex = something happened.
- **Available on GEE:** Yes (`NASA/VIIRS/002/VNP46A2`), which is the easiest integration path.

### How to Access Programmatically
1. **LANCE NRT direct download:** Register at earthdata.nasa.gov, use HTTP/HTTPS with bearer token auth. Wget/curl scripts or `requests` in Python.
2. **CMR (Common Metadata Repository) API:** Search for granules by bounding box + time. Returns download URLs.
3. **OPeNDAP/THREDDS:** Server-side subsetting (request only your AOI).
4. **Google Earth Engine:** Simplest path. `ee.ImageCollection('NASA/VIIRS/002/VNP46A2')` -- no file management needed.

### Verdict for Sentinel
**HIGH PRIORITY for Black Marble NTL.** Nighttime light anomalies are one of the strongest satellite-derived conflict indicators. Best accessed via GEE to avoid HDF5 file management. TROPOMI NRT is also valuable but lower resolution (5.5km) relative to hex-6 (~6.8km edge-to-edge), so you get roughly 1 data point per hex.

---

## 3. ESA Copernicus Beyond Sentinel Hub

### 3a. Copernicus Emergency Management Service (CEMS)
- **What:** Provides on-demand satellite-based damage assessments during emergencies (floods, fires, conflicts, humanitarian crises).
- **Products:** "Rapid Mapping" (within hours/days) and "Risk & Recovery Mapping" (post-event analysis). Each activation produces vector layers of damage extent, damage grading (Destroyed/Severe/Moderate), and affected population estimates.
- **Data format:** GeoJSON, GeoTIFF, Shapefiles, GeoDatabase. Downloadable via REST API.
- **API:** Full OpenAPI spec at `mapping.emergency.copernicus.eu`. JSON API for each activation with download URLs for vector/raster outputs. Can load layers directly in GIS clients.
- **Cost:** Completely free. All data publicly available.
- **Levant coverage:** CEMS has activated for Lebanon, Syria, and the broader region during the 2024 conflict escalation.
- **Conflict relevance:** CEMS activation data provides expert-verified building damage polygons that can serve as training/validation data for your own SAR models.
- **Integration priority:** Post-funding. Useful as validation data but activations are sporadic and event-driven. Not a continuous feed.

### 3b. Copernicus Climate Change Service (C3S) -- ERA5
- **What:** ERA5 is the world's most comprehensive climate reanalysis dataset. Hourly estimates of atmospheric, land, and oceanic variables from January 1940 to present.
- **Resolution:** ~31km (0.25 degree grid), hourly
- **Access:** Free via Climate Data Store (CDS) API (`pip install cdsapi`). Also on GEE as `ECMWF/ERA5_DAILY`.
- **Relevance:** You already use Open-Meteo for weather features. ERA5 is the underlying data source for Open-Meteo. Direct ERA5 access gives you more variables (soil moisture, boundary layer height, radiation components) but adds complexity.
- **Integration priority:** LOW. Open-Meteo is already a sufficient weather data proxy. ERA5 adds marginal value for conflict prediction specifically.

### 3c. Copernicus Atmosphere Monitoring Service (CAMS)
- **What:** Global and regional air quality analysis and forecasts. Provides modeled concentrations of PM2.5, PM10, O3, NO2, SO2, CO, and aerosols.
- **Resolution:** ~40km global, ~10km European domain
- **Access:** Free via Atmosphere Data Store (ADS) API (same infrastructure as CDS). Also on GEE as `ECMWF/CAMS/NRT`.
- **Relevance:** Modeled air quality can supplement TROPOMI observations. However, CAMS resolution (~40km) is coarser than hex-6 (~36 km^2) so you get roughly 1 value per hex at best. Direct TROPOMI data is higher resolution.
- **Integration priority:** LOW. TROPOMI direct observations via GEE are higher resolution and more directly useful.

### 3d. Copernicus Land Monitoring Service (CLMS)
- **What:** Land cover, land use change, vegetation indices, ground motion, water cycle data for Europe and globally.
- **Products:**
  - High Resolution Layers (HRLs): 10m annual layers for impervious surfaces, tree cover, grasslands, croplands, small woody areas, water/wetness across 38 European countries (includes Israel, Lebanon area).
  - CORINE Land Cover: 100m, updated every 6 years.
  - Global land cover products at various resolutions.
- **Access:** Free, open data. Migrating to Copernicus Data Space Ecosystem (CDSE) by end of 2026.
- **Relevance:** HRLs at 10m can provide a baseline land cover classification for the Levant. Year-over-year changes in impervious surface or vegetation could indicate construction, destruction, or agricultural abandonment.
- **Integration priority:** LOW for 2-week sprint. Useful as a baseline layer post-funding.

---

## 4. UNOSAT / UNITAR Damage Assessments

### What They Provide
UNOSAT (United Nations Satellite Centre, part of UNITAR) produces expert-analyzed satellite damage assessments for conflict and disaster zones. Analysts manually review very-high-resolution satellite imagery and label building-level damage.

### Granularity
- **Building-level.** Each structure is classified as:
  - **Destroyed** (complete structural failure)
  - **Severe Damage** (major structural damage visible)
  - **Moderate Damage** (partial damage visible)
- Data is delivered as vector polygons (shapefiles/geodatabase) with per-building attributes.

### Coverage for the Levant
- **Gaza:** Comprehensive damage assessments updated regularly (7+ assessment rounds as of 2025). Building-level data available on HDX and ArcGIS Hub.
- **Lebanon:** UNOSAT has products cataloged for Lebanon (see unosat.org/products/). The 2024 conflict produced significant damage data, particularly for southern Lebanon, Dahiyeh (south Beirut), and Baalbek-El Hermel. Check HDX for latest releases.
- **Syria:** Historical damage assessments exist for Aleppo, Homs, Damascus suburbs, and other areas from the civil war period.

### Can They Be Used as Training Data for SAR Models?
**Yes, this is their primary value for Sentinel.** UNOSAT building-level damage labels + building footprints (from OpenStreetMap or Google Open Buildings) + Sentinel-1 SAR imagery = supervised training data for a damage detection model. Both the PWTT paper and the ETH Zurich Nature 2025 paper use this approach.

### How to Access
1. **Humanitarian Data Exchange (HDX):** `data.humdata.org/organization/unosat` -- 218+ datasets, downloadable as shapefiles, GeoJSON.
2. **UNOSAT Products Portal:** `unosat.org/products/` -- browse by country/event.
3. **ArcGIS Hub:** `gaza-unosat.hub.arcgis.com/pages/data` -- Gaza-specific portal with interactive maps.
4. **Direct contact:** `unosat@unitar.org` for specific requests.

### Verdict for Sentinel
**MEDIUM-HIGH PRIORITY.** UNOSAT data is the gold standard for damage labels. Download the Lebanon and Gaza datasets now to use as training/validation data for SAR-based damage features. This is a one-time data acquisition, not a continuous pipeline.

---

## 5. Microsoft Planetary Computer

### What It Is
A cloud-based geospatial platform (similar to GEE but built on Azure) that hosts petabytes of environmental data in cloud-optimized formats (COG, Zarr, GeoParquet) with a STAC API for search and discovery.

### Datasets Available

| Dataset | Format | Resolution | Notes |
|---------|--------|------------|-------|
| Sentinel-1 GRD | COG | 10m | Full global archive from 2014 |
| Sentinel-2 L2A | COG | 10m | Full global archive from 2016 |
| Landsat Collection 2 | COG | 30m | Landsat 4-9 |
| ALOS PALSAR Mosaic | COG | 25m | Annual mosaics |
| ESA WorldCover | COG | 10m | 2020, 2021 |
| NASADEM | COG | 30m | DEM |
| ERA5 | Zarr | ~31km | Climate reanalysis |
| Sentinel-5P | Zarr | 5.5km | TROPOMI atmospheric |
| MODIS products | Various | Various | Vegetation, fire, etc. |
| Microsoft Building Footprints | GeoParquet | Building-level | ML-derived footprints globally |

### Is It Free?
- **Data catalog and STAC API:** Free for anyone, no account needed.
- **Data access:** Free. All data is on Azure Blob Storage with anonymous read access. You stream COG tiles directly -- no download of full scenes needed.
- **Compute (Hub):** Previously offered a free JupyterHub, but Planetary Computer Hub was retired. You can access data from any environment (your own machine, a VM, etc.).
- **No rate limits on data access** mentioned in documentation.

### Conflict-Relevant Features
- **Microsoft Building Footprints:** ML-derived building polygons for the entire globe. Essential for building-level damage assessment (overlay SAR change maps on building footprints).
- **STAC API:** Standards-based, so you can swap between Planetary Computer and AWS Earth Search with minimal code changes.
- **Cloud-optimized formats:** Stream only the bands/tiles you need without downloading full scenes.

### Verdict for Sentinel
**MEDIUM PRIORITY as an alternative data access path.** If you use GEE for compute, you don't need Planetary Computer for the same datasets. But the Microsoft Building Footprints dataset is uniquely valuable and not on GEE. Worth grabbing building footprints for the Levant from here.

**Key integration:** Download Microsoft Building Footprints for Lebanon/N. Israel/S. Syria, load into Supabase/PostGIS as a reference layer.

---

## 6. AWS Open Data / Google Public Datasets

### AWS Registry of Open Data -- Satellite Datasets

| Dataset | Format | STAC API | Notes |
|---------|--------|----------|-------|
| Sentinel-1 GRD COGs | Cloud-Optimized GeoTIFF | Earth Search (Element 84) | Free, full archive |
| Sentinel-2 L2A COGs | Cloud-Optimized GeoTIFF | Earth Search | Free, L2A from April 2017 (Europe), Dec 2018 (global). Updated within hours of Copernicus release |
| Landsat (USGS) | COG | Yes | Landsat 1-9, full archive |
| ESA WorldCover | COG | Yes | 10m, CC BY 4.0 |
| Capella Space SAR Open Data | SLC/GEC | Via Capella Console | X-band SAR, very high res samples (sub-meter). Limited geographic coverage in open program |
| OpenAerialMap | Various | Via OAM API | ~15,000 drone/aerial images |
| ALOS PALSAR/PALSAR-2 | Various | Via ASF | L-band SAR mosaics + FNF maps |
| NAIP (US only) | COG | Yes | Not relevant for Levant |

### Google Public Datasets (BigQuery)
- ERA5 climate data
- Global Fishing Watch (AIS vessel tracking -- could detect naval movements)
- OpenStreetMap extracts

### Key Takeaway
AWS and Google host mirrors of the same datasets available through GEE and Planetary Computer. The main advantage is if you want to do processing on your own infrastructure (EC2, Cloud Run) rather than GEE's managed compute. For a startup, GEE is almost always the better choice because you skip the infrastructure management.

### Verdict for Sentinel
**LOW PRIORITY as a primary access method.** Use GEE instead. AWS Earth Search STAC API is a good fallback if you hit GEE quotas or need SLC-level Sentinel-1 data (GEE only has GRD, not SLC).

---

## 7. OpenAerialMap

### What It Is
An open platform hosting ~15,000 drone/aerial/satellite images contributed by users worldwide, all CC BY 4.0. Run by Humanitarian OpenStreetMap Team (HOT).

### Coverage of the Levant
- **Sparse.** OpenAerialMap coverage depends on contributions. For the Levant:
  - Some coverage from the 2020 Beirut port explosion (Beirut Recovery Map project)
  - Sporadic drone imagery from humanitarian mapping efforts
  - No systematic coverage of southern Lebanon, northern Israel, or southern Syria
- You can check: `map.openaerialmap.org` and zoom to the Levant to see what's available.

### Conflict Relevance
- Very high resolution when available (drone imagery can be sub-10cm)
- Useful for validation of damage detection models (visual ground truth)
- Not a reliable data source for continuous monitoring

### Verdict for Sentinel
**LOW PRIORITY.** Check periodically for post-conflict imagery that could serve as visual validation, but do not build a pipeline around it. Coverage is too sporadic.

---

## 8. Pre-Processed Satellite-Derived Datasets

### 8a. Global Human Settlement Layer (GHSL)
- **Provider:** European Commission Joint Research Centre (JRC)
- **What:** Built-up area detection, building height/volume, population grids
- **Resolution:** 10m (2023 edition), 38m, 100m, and 1km versions
- **Temporal:** Multi-epoch (1975, 1990, 2000, 2005, 2010, 2015, 2020, 2025, 2030 projected)
- **Access:** Free, open. Available on GEE (`JRC/GHSL/P2023A/GHS_BUILT_S`), JRC Data Catalogue, direct download
- **Relevance:** Baseline built-up surface area for each hex. Pre-conflict built-up area vs. post-conflict SAR damage = destruction percentage. Also useful as a population exposure proxy.
- **Priority:** MEDIUM. One-time download for baseline, not continuous.

### 8b. Dynamic World (Google)
- **What:** Near-real-time 10m land use/land cover classification using deep learning on Sentinel-2
- **9 Classes:** Trees, Shrubs, Grass, Crops, Water, Flooded Vegetation, Bare Ground, Snow/Ice, Built-up (buildings/roads)
- **Resolution:** 10m, updated every 2-5 days (matches Sentinel-2 cadence)
- **Access:** Free on GEE (`GOOGLE/DYNAMICWORLD/V1`). Interactive viewer at dynamicworld.app.
- **Relevance:** **Very high.** Real-time detection of:
  - Built-up to bare ground transitions = building destruction
  - Crops to bare ground = agricultural damage
  - Any land cover class to water = flooding from dam strikes
  - Provides per-pixel probability scores, not just labels
- **Priority:** **HIGH.** One of the easiest conflict indicators to compute per-hex. Just aggregate Dynamic World class probabilities over each hex and track changes.

### 8c. ESA WorldCover
- **What:** 10m global land cover map from Sentinel-1 + Sentinel-2
- **11 Classes:** Tree cover, Shrubland, Grassland, Cropland, Built-up, Bare/sparse, Snow/Ice, Water, Herbaceous Wetland, Mangrove, Moss/Lichen
- **Versions:** v100 (2020), v200 (2021)
- **Access:** Free (CC BY 4.0). On GEE, AWS, Terrascope, direct download.
- **Relevance:** Static baseline land cover. Use as a feature in your XGBoost model (what type of terrain is each hex?). Compare with Dynamic World temporal data to detect changes.
- **Priority:** MEDIUM. One-time ingest as a static feature layer.

### 8d. Global Forest Watch
- **What:** Near-real-time deforestation alerts, fire alerts, tree cover loss data
- **Fire alerts:** Daily, from VIIRS/MODIS (you already have this via FIRMS)
- **Deforestation alerts (GLAD):** Weekly, 30m resolution
- **RADD alerts:** 10m, tropics only
- **API:** RESTful, returns JSON/GeoJSON. Free, no key required for most endpoints. Custom geometry queries supported.
- **Relevance:** Marginal for the Levant. The region is not heavily forested. Fire alerts overlap with FIRMS which you already use. Deforestation is not a primary conflict indicator here.
- **Priority:** LOW. Skip.

### 8e. DMSP-OLS Nighttime Lights (Historical)
- **What:** Annual nighttime lights composites from 1992-2014
- **Resolution:** ~1km (30 arc-seconds)
- **Access:** Free. On GEE (`NOAA/DMSP-OLS/NIGHTTIME_LIGHTS`), NOAA/NCEI direct download.
- **Relevance:** Historical baseline only. VIIRS (2012-present) supersedes this with much better resolution (500m vs 1km) and calibration. Could be useful for long-term historical analysis (pre-2011 Syria baseline) but not for real-time prediction.
- **Priority:** LOW. Skip for now.

---

## 9. Synthetic Aperture Radar (SAR)

### 9a. Sentinel-1 (C-band, 5.4 GHz)
- **Status:** Sentinel-1A operational. Sentinel-1B failed in Dec 2021, Sentinel-1C launched Dec 2024.
- **Resolution:** 10m (IW mode GRD), 5x20m (IW SLC for interferometry)
- **Revisit:** 6 days (with 2 satellites), 12 days with 1
- **Access:** Free. GEE (GRD only), AWS (GRD COGs), Copernicus Data Space (GRD + SLC)
- **Key limitation in GEE:** Only GRD (amplitude) data, not SLC (complex). For coherence-based methods, you need SLC data from Copernicus Data Space or ASF.

### 9b. Sentinel-1 InSAR for Ground Deformation
- Uses SLC (Single Look Complex) data, NOT available in GEE
- Measures surface displacement with mm precision
- Could detect subsidence from tunnel collapse, structural deformation from bombing
- Requires significant processing (coregistration, interferogram generation, phase unwrapping)
- Tools: SNAP (ESA), ISCE2 (NASA), MintPy, EZ-InSAR
- **Priority for Sentinel:** LOW. Too complex for 2-week sprint. Amplitude-based methods (PWTT) are much simpler and nearly as effective for building damage.

### 9c. ALOS PALSAR / PALSAR-2 (L-band, 1.27 GHz)
- **Operator:** JAXA
- **What:** L-band SAR (longer wavelength, penetrates vegetation better than C-band)
- **Resolution:** 25m (mosaic products), 10m (ScanSAR), 3m (Fine mode)
- **Temporal:** Annual mosaics from 2007 (PALSAR) and 2015 (PALSAR-2) to present
- **Access:** Free. Level 1.1 from JAXA G-Portal, mosaic products on GEE and AWS. ALOS-2 PALSAR-2 ScanSAR via ASF DAAC (Earthdata login).
- **Relevance:** L-band complements C-band (Sentinel-1). Better for vegetated areas where C-band saturates. Annual mosaics can detect long-term land cover change. Not useful for rapid change detection (annual resolution).
- **Priority:** LOW. Not useful for near-real-time conflict monitoring. Post-funding for historical analysis.

### 9d. NISAR (NASA/ISRO)
- **Status:** Launched July 30, 2025. Commissioned November 2025. Fully operational January 2026.
- **Bands:** L-band (NASA) + S-band (ISRO). First-ever dual-frequency SAR satellite.
- **Resolution:** ~10m
- **Revisit:** 12 days (ascending + descending = ~6 day average)
- **Data policy:** Free and open. Available within 1-2 days of observation, within hours for emergencies. Distributed by ASF DAAC.
- **Relevance:** **Game-changer.** L-band SAR at 12-day revisit for free. L-band penetrates smoke/haze better than C-band, important in conflict zones. Dual-frequency enables better damage classification.
- **Priority:** MEDIUM-HIGH but patience required. Data is flowing now but the ecosystem (GEE ingestion, analysis tools) is still maturing. Plan to integrate by Q3 2026.

### 9e. SAR Coherence Change Detection
The most powerful SAR-based conflict damage detection method. Key concepts:
- **Coherence:** Measure of phase stability between two SAR images. High coherence = stable scene. Low coherence = something changed.
- **Pre-event pair coherence vs. co-event pair coherence:** If coherence drops, buildings were damaged/destroyed.
- **Requires SLC data** (not GRD). Cannot be done in GEE alone.
- **Tools:**
  - **ESA SNAP:** Free, Java-based, GUI + command line (GPT). Full Sentinel-1 SLC processing chain. `snap/bin/gpt` for batch processing.
  - **ISCE2:** NASA's InSAR Scientific Computing Environment. Python-based, MIT-like license. Best for research-grade InSAR.
  - **ASF MapReady:** Alaska Satellite Facility's SAR processing toolkit. Free.
  - **sarsen (xarray-based):** Python library for SAR data on xarray. Newer, simpler API.
- **Priority for Sentinel:** Post-funding. Amplitude-based PWTT on GEE is the 2-week sprint option. Coherence requires SLC download + local/cloud processing.

### 9f. Capella Space (X-band, 9.65 GHz)
- **Resolution:** Sub-meter (0.5m spot mode)
- **Open Data Program:** Free samples available on AWS. CC BY 4.0.
- **Relevance:** Ultra-high-resolution SAR for detailed damage assessment. Very limited free data. Full tasking costs $$$.
- **Priority:** LOW. Check open data gallery for any Levant coverage, but don't build around it.

---

## 10. Conflict-Specific Satellite Analysis Tools

### 10a. PWTT (Pixel-Wise T-Test)
- **Author:** Ollie Ballinger (UCL)
- **Paper:** "Open Access Battle Damage Detection via Pixel-Wise T-Test on Sentinel-1 Imagery" (Remote Sensing of Environment, 2025)
- **Code:** github.com/oballinger/PWTT (open source)
- **Method:** Compare mean SAR amplitude of pre-conflict and post-conflict image stacks using per-pixel t-test. Statistically significant drops in backscatter = building damage.
- **Accuracy:** Tested on 2M+ labeled building footprints across 30 cities in Palestine, Ukraine, Sudan, Syria, Iraq.
- **GEE compatible:** Yes. Uses Sentinel-1 GRD.
- **Resolution:** 10m (Sentinel-1 native)
- **Used by:** The Economist (Ukraine damage assessment), major media organizations for Gaza
- **Priority:** **HIGHEST.** This is the single most relevant open-source tool for Sentinel. It was literally designed for exactly your use case.

### 10b. ETH Zurich War Destruction Mapping Tool
- **Paper:** "An open-source tool for mapping war destruction at scale in Ukraine using Sentinel-1 time series" (Nature Communications Earth & Environment, 2025)
- **Code:** github.com/prs-eth/ukraine-damage-mapping-tool (MIT License)
- **Method:** ML model trained on SAR time series + existing damage labels + open building footprints. Generates probabilistic damage estimates at building level.
- **Platform:** Runs on Google Earth Engine.
- **Outputs:** Two dashboards -- Ukraine Damage Explorer (precomputed) and Rapid Damage Mapping Tool (on-demand).
- **Confidence intervals:** Adjustable by user, enabling flexible assessments.
- **Priority:** **HIGH.** More sophisticated than PWTT (ML vs. statistical test) but also more complex. Good Phase 2 after PWTT.

### 10c. Bellingcat Tools
- **Shadow Finder Tool:** Narrows down image geolocation by analyzing shadow angles. Not directly useful for automated conflict prediction.
- **SunCalc:** Models sun position/shadow length for a given date/time/location. Useful for OSINT but not for automated pipelines.
- **ATLOS:** Open-source collaborative platform for organizing geolocated incidents. Could be useful for data labeling/verification but not for automated features.
- **Priority:** LOW for automated pipeline. Useful for manual investigation/verification.

### 10d. Refugee Camp / Displacement Monitoring
- **Methods:**
  - Sentinel-2 image classification for detecting informal settlement expansion/contraction (83-93% accuracy)
  - SAR-based (Sentinel-1 + ALOS-2) land cover classification around known camp locations
  - Deep learning (Mask R-CNN) on VHR imagery for individual dwelling detection
- **Free data approach:** Use Sentinel-2 + Dynamic World to detect new built-up areas near borders or known displacement corridors. Track hex-level changes in the "built-up" class probability.
- **Priority:** MEDIUM. Can be derived from Dynamic World data you'd already be ingesting.

### 10e. Agricultural Damage Detection
- **Methods:**
  - NDVI time series anomaly detection using Sentinel-2 or MODIS
  - Sentinel-2 spectral bands + vegetation indices + Random Forest classifier
  - Year-over-year cropland comparison using Dynamic World
- **Evidence from Ukraine:** ~500,000 hectares of cropland classified as damaged across 10 regions in 2022, with 66-80% of fire activity concentrated within 30km of the front line.
- **Free data:** Sentinel-2 (10m, 5-day revisit), MODIS NDVI (250m-1km, daily-16day)
- **Priority:** MEDIUM. NDVI anomaly per hex is a straightforward XGBoost feature to compute via GEE.

---

## 11. Air Quality / Atmospheric as Conflict Indicators

### Sentinel-5P TROPOMI
| Product | Resolution | Revisit | GEE Collection |
|---------|-----------|---------|----------------|
| NO2 (tropospheric) | 5.5 x 3.5 km | Daily | `COPERNICUS/S5P/OFFL/L3_NO2` |
| SO2 | 5.5 x 3.5 km | Daily | `COPERNICUS/S5P/OFFL/L3_SO2` |
| CO | 5.5 x 7 km | Daily | `COPERNICUS/S5P/OFFL/L3_CO` |
| Aerosol Index (UVAI) | 5.5 x 3.5 km | Daily | `COPERNICUS/S5P/OFFL/L3_AER_AI` |
| CH4 | 5.5 x 7 km | Daily | `COPERNICUS/S5P/OFFL/L3_CH4` |
| HCHO (formaldehyde) | 5.5 x 3.5 km | Daily | `COPERNICUS/S5P/OFFL/L3_HCHO` |

### Can These Detect Conflict Activity?

**YES -- with nuance.** Published research from Gaza, Ukraine, Sudan, and Iraq confirms:

| Indicator | What It Detects | Evidence |
|-----------|----------------|----------|
| UVAI (Aerosol Index) | Smoke plumes from fires/explosions | **Sharp, sustained increases** in Gaza linked to widespread combustion and infrastructure damage |
| CO | Sustained burning, infrastructure fires | **Sustained increases** in conflict zones |
| SO2 | Fuel depot destruction, generator use | **Episodic spikes** tied to specific target destruction |
| NO2 | Complex -- decreases from economic shutdown, increases from military activity in active combat areas | In Ukraine, Kharkiv showed **significant NO2 increase** from war activity; eastern regions showed **decrease** from population displacement |
| CH4 | Collapse of waste management systems | **Steady rise** in Gaza post-conflict onset |

### Are These Useful at Hex-Level Resolution?
**Marginally.** TROPOMI's 5.5km pixel size is close to the edge length of an H3 hex-6 cell (~6.8km). You'll get roughly 1-2 TROPOMI pixels overlapping each hex. This means:
- You won't see fine spatial gradients within a hex
- You CAN detect anomalies at the hex level (sudden spike vs. baseline for that hex)
- Best used as a supplementary signal, not a primary feature

### Novel Integration Method
A 2025 paper describes combining InSAR coherence change detection WITH air quality satellites to study conflict effects. This multi-modal approach (SAR damage + atmospheric anomalies) could be powerful for your model.

### Verdict for Sentinel
**MEDIUM PRIORITY.** TROPOMI is easy to integrate via GEE (just another `reduceRegions` call per hex). The atmospheric anomaly features add a genuinely novel signal that most conflict prediction systems don't use. Worth including in a 2-week sprint alongside SAR and nighttime lights.

---

## 12. Other Platforms and Datasets

### 12a. Descartes Labs
- **Status:** Acquired by EarthDaily Analytics in October 2024. No longer operates independently.
- **Verdict:** SKIP. Platform is being absorbed into EarthDaily's commercial offering.

### 12b. UP42
- **What:** Marketplace for satellite data and analytics from 50+ providers.
- **Pricing:** Credit-based (100 credits = 1 EUR). No free tier beyond browsing. Pay-per-use.
- **Verdict:** SKIP for now. All the data you need is available free through GEE, AWS, or Planetary Computer.

### 12c. SkyFi
- **What:** Self-service platform for tasking satellites and purchasing archive imagery.
- **Open Data:** SkyFi offers a "Free Satellite Imagery & Geospatial Data" section with some openly licensed data.
- **Pricing:** Pay-per-image for tasking. No free tier for tasking.
- **Verdict:** LOW. Check the free data section for any Levant coverage. Not a pipeline dependency.

### 12d. EarthRanger
- **What:** Open-source platform for ecosystem monitoring by Allen Institute for AI (Ai2). Deployed at 600+ sites across 74 countries.
- **Focus:** Conservation (anti-poaching, wildlife tracking). Not designed for conflict monitoring.
- **Components:** Core Server, API, Web App, Mobile App, sensor integrations.
- **Verdict:** SKIP. Wrong domain. Could theoretically be repurposed but there are better tools for conflict.

### 12e. Open Data Cube (ODC)
- **What:** Free, open-source Python library for managing and analyzing large satellite imagery archives on your own infrastructure.
- **Verdict:** SKIP. GEE handles this better for your use case without the infrastructure overhead.

### 12f. World Monitor
- **What:** Open-source real-time situational awareness platform that aggregates 100+ news feeds, military flight tracking, naval vessel monitoring, satellite fire detection, conflict zone mapping, and infrastructure data.
- **Relevance:** Potential complementary data source (AIS vessel tracking, military flight data). Not a satellite platform per se but an intelligence aggregator.
- **Priority:** POST-FUNDING. Interesting for enriching the alert narrative but not core to the XGBoost model.

### 12g. Capella Space Open Data
- **What:** Sub-meter X-band SAR imagery. Free samples on AWS (CC BY 4.0).
- **Access:** Registry of Open Data on AWS, Capella Console, or apply for Data Cooperative/Grant.
- **Coverage:** Global samples, not systematic. Check gallery for Levant coverage.
- **Priority:** LOW. Check once for any useful samples, but don't build a pipeline.

### 12h. Microsoft Building Footprints
- **What:** ML-derived building footprints for the entire globe. Available on Planetary Computer as GeoParquet.
- **Relevance:** **HIGH.** Essential reference layer for translating SAR damage pixels into "number of damaged buildings per hex." Cross-reference with UNOSAT damage labels.
- **Priority:** MEDIUM-HIGH. One-time download and load into Supabase/PostGIS.

### 12i. Google Open Buildings
- **What:** Similar to Microsoft Building Footprints but from Google. 1.8B+ building footprints globally. Available on GEE.
- **Relevance:** Same use case as Microsoft footprints. Choose whichever has better coverage for the Levant.
- **Priority:** MEDIUM-HIGH (same as Microsoft). Compare coverage quality.

---

## 13. Priority Matrix: What to Integrate When

### 2-Week Sprint (Pre-Funding MVP Features)

| Source | Feature for XGBoost | Integration Path | Effort |
|--------|-------------------|------------------|--------|
| **GEE + Sentinel-1 SAR** | PWTT damage score per hex | GEE Python API + `reduceRegions` | 3-4 days |
| **GEE + VIIRS Black Marble** | Nighttime light anomaly per hex (delta from 30-day baseline) | GEE Python API | 1-2 days |
| **GEE + TROPOMI NO2/Aerosol** | Atmospheric anomaly per hex | GEE Python API | 1 day |
| **GEE + Dynamic World** | Land cover change probability per hex (built-up delta, crop delta) | GEE Python API | 1-2 days |
| **UNOSAT damage labels** | Validation data for damage features | Download shapefiles from HDX | 0.5 day |

**Total new features:** 5-8 satellite-derived features per hex, all via a single GEE pipeline.

### Post-Funding (Month 2-3)

| Source | Feature/Use | Notes |
|--------|-------------|-------|
| NISAR L-band SAR | Complementary damage detection | Data flowing now, ecosystem maturing |
| SAR coherence (SLC) | Higher-fidelity damage detection | Requires SLC processing pipeline |
| ETH Zurich damage tool | ML-based probabilistic damage | More sophisticated than PWTT |
| Microsoft/Google Building Footprints | Building count per hex, damage count | Load into PostGIS |
| GHSL | Built-up area baseline | One-time ingest |
| CEMS activation data | Validation/training data | Event-driven, not continuous |
| NDVI agricultural damage | Cropland damage per hex | Sentinel-2 via GEE |

### Nice-to-Have (Quarter 2+)

| Source | Feature/Use | Notes |
|--------|-------------|-------|
| InSAR ground deformation | Tunnel collapse, structural damage | Requires significant SAR expertise |
| CAMS air quality models | Supplementary atmospheric | Coarser than TROPOMI |
| AIS vessel tracking | Naval movement patterns | From World Monitor or Marine Traffic |
| ERA5 reanalysis | Enhanced weather features | Marginal over Open-Meteo |

---

## Key Recommendations

1. **Google Earth Engine is the central platform.** Everything you need for a 2-week sprint (Sentinel-1, VIIRS NTL, TROPOMI, Dynamic World) is on GEE with a Python API. Register a noncommercial project today (free 150 EECU-hours/month on Community tier).

2. **The PWTT algorithm is purpose-built for Sentinel's use case.** It was literally tested on Palestine, Syria, and other Levant-adjacent conflicts. Run it on GEE, aggregate to H3 hexes, feed to XGBoost.

3. **Nighttime lights are the lowest-hanging fruit.** VIIRS Black Marble daily NTL on GEE. Compute 30-day rolling mean per hex, then flag deviations. Power outages and destruction create dramatic NTL drops.

4. **TROPOMI atmospheric data is a novel signal most conflict prediction systems miss.** Aerosol index and CO spikes are proven conflict indicators. Resolution is coarse but still hex-level meaningful.

5. **Dynamic World gives you real-time land cover change for free.** Built-up to bare ground transitions = destruction. Crop to bare ground = agricultural damage. All at 10m, updated every 5 days.

6. **Download UNOSAT damage labels NOW** even if you don't use them immediately. They're the ground truth for training and validating any SAR-based damage feature.

7. **Microsoft/Google Building Footprints** give you the denominator for "what percentage of buildings in this hex are damaged." Essential reference layer.

8. **NISAR is the next big thing** but wait for the GEE ingestion and tooling to mature before investing time.

---

## Sources

- [GEE Noncommercial Tiers](https://developers.google.com/earth-engine/guides/noncommercial_tiers)
- [GEE Pricing](https://cloud.google.com/earth-engine/pricing)
- [GEE Quotas](https://developers.google.com/earth-engine/guides/usage)
- [GEE Data Catalog](https://developers.google.com/earth-engine/datasets)
- [GEE Python API Intro](https://developers.google.com/earth-engine/tutorials/community/intro-to-python-api)
- [GEE Zonal Statistics with H3](https://expertbeacon.com/zonal-statistics-with-google-earth-engine-and-h3-hexagons/)
- [World Bank GEE_Zonal](https://github.com/worldbank/GEE_Zonal)
- [NASA LANCE NRT](https://nrt3.modaps.eosdis.nasa.gov/)
- [VIIRS Black Marble](https://blackmarble.gsfc.nasa.gov/)
- [VNP46A2 on GEE](https://developers.google.com/earth-engine/datasets/catalog/NASA_VIIRS_002_VNP46A2)
- [CEMS Mapping Portal](https://mapping.emergency.copernicus.eu/)
- [CEMS API](https://mapping.emergency.copernicus.eu/about/risk-and-recovery-manual/online-resources/api-layers/)
- [Climate Data Store (ERA5)](https://cds.climate.copernicus.eu/)
- [CAMS Data](https://atmosphere.copernicus.eu/data)
- [CLMS Products](https://land.copernicus.eu/en/products)
- [UNOSAT on HDX](https://data.humdata.org/organization/unosat)
- [UNOSAT Products Portal](https://unosat.org/products/)
- [UNOSAT Gaza Data Download](https://gaza-unosat.hub.arcgis.com/pages/data)
- [Planetary Computer Data Catalog](https://planetarycomputer.microsoft.com/catalog)
- [Planetary Computer STAC API](https://planetarycomputer.microsoft.com/docs/quickstarts/reading-stac/)
- [AWS Sentinel-2 COGs](https://registry.opendata.aws/sentinel-2-l2a-cogs/)
- [AWS Sentinel-1](https://registry.opendata.aws/sentinel-1/)
- [OpenAerialMap](https://openaerialmap.org/)
- [Dynamic World](https://dynamicworld.app/about/)
- [Dynamic World on GEE](https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_DYNAMICWORLD_V1)
- [GHSL](https://human-settlement.emergency.copernicus.eu/)
- [GHSL on GEE](https://developers.google.com/earth-engine/datasets/catalog/JRC_GHSL_P2023A_GHS_BUILT_S)
- [ESA WorldCover](https://esa-worldcover.org/en)
- [Global Forest Watch](https://www.globalforestwatch.org/)
- [DMSP-OLS on GEE](https://developers.google.com/earth-engine/datasets/catalog/NOAA_DMSP-OLS_NIGHTTIME_LIGHTS)
- [PWTT GitHub](https://github.com/oballinger/PWTT)
- [PWTT Paper (arXiv)](https://arxiv.org/abs/2405.06323)
- [PWTT Paper (Remote Sensing of Environment)](https://www.sciencedirect.com/science/article/pii/S0034425725004298)
- [ETH Zurich Damage Mapping Tool](https://github.com/prs-eth/ukraine-damage-mapping-tool)
- [ETH Zurich Paper (Nature)](https://www.nature.com/articles/s43247-025-02183-7)
- [Bellingcat Toolkit](https://bellingcat.gitbook.io/toolkit)
- [Bellingcat Shadow Finder](https://www.bellingcat.com/resources/2024/08/22/shadow-geolocate-geolocation-locate-image-tool-open-source-bellingcat-measure/)
- [ALOS PALSAR Open Data (JAXA)](https://www.eorc.jaxa.jp/ALOS/en/dataset/alos_open_and_free_e.htm)
- [ALOS PALSAR at ASF DAAC](https://asf.alaska.edu/datasets/daac/alos-palsar/)
- [NISAR Mission Overview](https://science.nasa.gov/mission/nisar/mission-overview/)
- [NISAR Data Access (Earthdata)](https://www.earthdata.nasa.gov/news/now-that-nisar-launched-heres-what-you-can-expect-from-the-data)
- [ISCE2 (InSAR)](https://github.com/isce-framework/isce2)
- [Awesome SAR Resources](https://github.com/RadarCODE/awesome-sar)
- [SNAP (ESA)](https://step.esa.int/)
- [Sentinel-5P TROPOMI](https://sentiwiki.copernicus.eu/web/s5p-applications)
- [TROPOMI on GEE](https://developers.google.com/earth-engine/datasets/tags/tropomi)
- [Air Pollution Gaza Study](https://www.sciencedirect.com/science/article/pii/S0959378025000810)
- [Ukraine Air Pollution from Conflict](https://www.mdpi.com/2071-1050/14/21/13832)
- [InSAR + Air Quality Conflict Study](https://www.sciencedirect.com/science/article/pii/S1569843225003346)
- [Agricultural Damage Ukraine (Sentinel-2)](https://www.sciencedirect.com/science/article/pii/S1569843223003862)
- [Cropland Losses Ukraine](https://www.frontiersin.org/journals/earth-science/articles/10.3389/feart.2019.00305/full)
- [Capella Space Open Data (AWS)](https://registry.opendata.aws/capella_opendata/)
- [Capella Open Data Program](https://support.capellaspace.com/what-is-the-capella-open-data-program)
- [EarthRanger](https://www.earthranger.com/)
- [Open Data Cube](https://www.opendatacube.org/)
- [Lebanon Damage Assessment (Amnesty)](https://www.amnesty.org/en/latest/research/2025/08/israel-lebanon-extensive-destruction/)
- [Refugee Camp Monitoring (Sentinel-1)](https://www.mdpi.com/2072-4292/11/17/2047)
