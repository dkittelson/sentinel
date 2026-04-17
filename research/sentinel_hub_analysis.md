# Sentinel Hub / Copernicus — Free Satellite Data Analysis

## What It Is
Sentinel Hub is a cloud-based satellite imagery processing service (originally Sinergise, acquired by Planet Labs Aug 2023). It won ESA's 2016 Copernicus Masters grand prize. Provides on-the-fly processing of satellite data via RESTful APIs.

## Free Access: Copernicus Data Space Ecosystem (CDSE)
**URL:** dataspace.copernicus.eu — free, instant registration, no credit card.

**Free tier includes:**
- 10,000 Sentinel Hub Processing Units (PUs) per month (reset 1st, no rollover)
- 12 TB monthly download transfer
- Full Sentinel Hub API access (Process, Statistical, Batch Statistical, Catalog)
- openEO credits (10,000/month)

## Free Satellite Data Available

| Collection | Type | Resolution | Revisit | Conflict Use |
|---|---|---|---|---|
| **Sentinel-1** | C-band SAR | 5-20m | 12 days | Building damage via coherence loss |
| **Sentinel-2 L1C/L2A** | Multispectral | 10-60m | 5 days | NDVI, NBR, burned area, change detection |
| **Sentinel-3** | Ocean/land | 300m-1km | <2 days | Large-scale vegetation monitoring |
| **Sentinel-5P** | Atmospheric | 7km | Daily | NO2/aerosol plumes (bombing signatures) |
| **Landsat 4-9** | Optical | 30m | 16 days | Long time series |
| **MODIS** | Multi-purpose | 250m-1km | Daily | High-frequency monitoring |
| **Copernicus DEM** | Elevation | 30m | Static | Terrain for routing |

**NOT on Sentinel Hub:** VIIRS/Black Marble nighttime lights → get from NASA Earthdata (also free).

## APIs
- **Process API** — send AOI + time + evalscript, get processed imagery (~1 PU per 512x512 output)
- **Statistical API** — returns JSON stats (mean, median, percentiles) instead of images. Perfect for per-H3-hex time series
- **Batch Statistical API** — up to 700,000 polygons at once. Ideal for all 4,735 Levant hexes
- **Catalog API** — STAC-compliant metadata search
- **Evalscripts** — custom JavaScript running server-side (Chrome V8). Can compute NDVI, NBR, coherence proxies without downloading raw data

## Conflict-Relevant Published Research
- **PWTT** (arXiv:2405.06323): AUC=0.88 building damage from S1, one line of GEE code
- **LT-CCD InSAR** (arXiv:2506.14730): 92.5% UNOSAT damage detection in Gaza, 1.2% FPR
- **Open-source war destruction tool** (Nature 2025): S1 time series, validated Ukraine
- **S1+S2 fusion for Mosul**: combined SAR + optical outperforms either alone

## Startup Programs
- **ESA Business Applications**: 1 year free access + 10 hours support
- **ESA Network of Resources**: sponsored accounts for research
- **CDSE Quota Increases**: for EU-funded/Copernicus projects
- **ESA BIC**: funding + technical support for EO startups in ESA member states

## Bottom Line for Sentinel
1. Register at dataspace.copernicus.eu (free, instant)
2. Use Statistical API to get per-H3-hex NDVI/NBR stats as JSON → feed into XGBoost
3. Sentinel-1 coherence change → building damage detection per hex (papers prove this for Gaza/Syria)
4. Apply for ESA Business Applications 1-year free account
5. VIIRS nighttime lights: separate pipeline from NASA Earthdata
