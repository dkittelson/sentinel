import pandas as pd
import numpy as np
import requests
import os
import h3
import rasterio
from shapely.geometry import box, Polygon
import geopandas as gpd
from rasterstats import zonal_stats
from rasterio.transform import from_bounds
from dotenv import load_dotenv

load_dotenv()

WORLDPOP_URLS = {
    "LB": "https://data.worldpop.org/GIS/Population/Global_2000_2020_1km/2020/LBN/lbn_ppp_2020_1km_Aggregated.tif",
    "SY": "https://data.worldpop.org/GIS/Population/Global_2000_2020_1km/2020/SYR/syr_ppp_2020_1km_Aggregated.tif",
    "IL": "https://data.worldpop.org/GIS/Population/Global_2000_2020_1km/2020/ISR/isr_ppp_2020_1km_Aggregated.tif",
}

def ingest_worldpop(output_path="data/processed/worldpop_hex.parquet"):
    if os.path.exists(output_path):
        print(f"Cache hit: {output_path}")
        return
    
    # Need a hex grid to calculate zonal stats
    # - Levant bounding box, convert to H3 hex IDs res 6, build polygons for each hex, GeoDataFrame
    roi = gpd.GeoDataFrame(geometry=[box(34.5, 32.5, 37.5, 34.8)], crs="EPSG:4326")
    hex_ids = h3.geo_to_cells(roi.geometry[0], 6)
    hex_polygons = [
        (hex_id, Polygon([(c[1], c[0]) for c in h3.cell_to_boundary(hex_id)]))
        for hex_id in hex_ids
    ]
    hex_gdf = gpd.GeoDataFrame(hex_polygons, columns=["h3_id", "geometry"], crs="EPSG:4326")
    
    # Need to calculate zonal stats for each hex
    # - Loop through each country and downloads data, calculates zonal stats within each hex, append one row per hex per country to list
    os.makedirs("data/raw", exist_ok=True) 
    records = []
    for country, url in WORLDPOP_URLS.items():
        tif_path = f"data/raw/worldpop_{country}.tif"
        if not os.path.exists(tif_path):
            raw = requests.get(url).content
            with open(tif_path, "wb") as f:
                f.write(raw)
        with rasterio.open(tif_path) as src:
            arr = src.read(1).astype(float)
            arr[arr < 0] = np.nan 
            transform = src.transform
        stats = zonal_stats(hex_gdf, arr, affine=transform, stats=["sum"], nodata=np.nan)
        for hex_id, stat in zip(hex_gdf["h3_id"], stats):
            records.append({"h3_id": hex_id, "population": stat["sum"] or 0})

    # Aggregate in cases where hexes overlap between two country rasters
    agg = pd.DataFrame(records).groupby("h3_id").agg(population=("population", "sum")).reset_index()

    # Save file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    agg.to_parquet(output_path, index=False)
    print(f"Saved {len(agg)} rows to {output_path}")  

if __name__ == "__main__":
    ingest_worldpop()

