import pandas as pd
import numpy as np
import os
import h5py
import earthaccess
from dotenv import load_dotenv
from shapely.geometry import box, Polygon
import geopandas as gpd
import h3
from rasterstats import zonal_stats
from rasterio.transform import from_bounds

load_dotenv()
NASA_TOKEN = os.getenv("EARTHDATA_TOKEN")

BBOX = [34.5, 32.5, 37.5, 34.8]  # [min_lon, min_lat, max_lon, max_lat]

def ingest_nightlights(output_path="data/processed/nightlights_hex_daily.parquet"):

    if os.path.exists(output_path):
        print(f"Cache hit: {output_path}")
        return

    # --- Create Lat/Lon Bounding Box to Capture Levant ---
    roi = gpd.GeoDataFrame(geometry=[box(34.5, 32.5, 37.5, 34.8)], crs="EPSG:4326")

    # --- Build H3 Hex Grids within roi for ML Model ---
    hex_ids = h3.geo_to_cells(roi.geometry[0], 6)
    hex_polygons = [
        (hex_id, Polygon([(coord[1], coord[0]) for coord in h3.cell_to_boundary(hex_id)]))
        for hex_id in hex_ids
    ]
    hex_gdf = gpd.GeoDataFrame(hex_polygons, columns=["h3_id", "geometry"], crs="EPSG:4326")

    # --- Download VNP46A2 tiles from NASA Earthdata ---
    earthaccess.login(strategy="environment")
    results = earthaccess.search_data(
        short_name="VNP46A2",
        bounding_box=(34.5, 32.5, 37.5, 34.8),
        temporal=("2020-01-01", "2025-12-31")
    )
    files = earthaccess.download(results, "data/raw/nightlights/")

    # --- Zonal Stats per HDF5 file (one file = one day) ---
    records = []
    transform = from_bounds(34.5, 32.5, 37.5, 34.8, 100, 100)  # approximate, updated per file

    for filepath in files:
        # HDF5 files contain multiple datasets — open and extract the NTL layer
        with h5py.File(filepath, "r") as f:
            # The NTL layer lives at this path inside the HDF5 file
            arr = f["HDFEOS/GRIDS/VIIRS_Grid_DNB_2d/Data Fields/DNB_BRDF-Corrected_NTL"][:]

        # arr is a 2D numpy array of pixel values for this day
        # replace fill values (65535) with NaN
        arr = arr.astype(float)
        arr[arr == 65535] = np.nan

        # recompute transform for actual pixel dimensions
        height, width = arr.shape
        transform = from_bounds(34.5, 32.5, 37.5, 34.8, width, height)

        # extract date from filename (format: VNP46A2.A2024001.h20v05....)
        # the date part is like A2024001 = year 2024, day-of-year 001
        basename = os.path.basename(filepath)
        year = int(basename.split(".")[1][1:5])
        doy = int(basename.split(".")[1][5:8])
        date = pd.Timestamp(year=year, month=1, day=1) + pd.Timedelta(days=doy - 1)

        # run zonal stats
        stats = zonal_stats(hex_gdf, arr, affine=transform, stats=["mean"], nodata=np.nan)
        for hex_id, stat in zip(hex_gdf["h3_id"], stats):
            records.append({"h3_id": hex_id, "date": date.date(), "ntl_mean": stat["mean"]})

    df = pd.DataFrame(records)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_parquet(output_path, index=False)
    print(f"Saved {len(df)} rows to {output_path}")

if __name__ == "__main__":
    ingest_nightlights()