import os
import duckdb
import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import Polygon, Point
import rasterio
import h3
import warnings
warnings.filterwarnings('ignore')

from src.spatial_engine import SpatialEngine

def create_h3_grid(gdf, resolution=7):
    """Generate H3 hex grid covering the given GeoDataFrame."""
    print(f"Generating H3 grid at resolution {resolution}...")
    bounds = gdf.total_bounds # [minx, miny, maxx, maxy]
    
    bbox_poly = Polygon([
        (bounds[0], bounds[1]),
        (bounds[0], bounds[3]),
        (bounds[2], bounds[3]),
        (bounds[2], bounds[1])
    ])
    
    geo_json = {
        "type": "Polygon",
        "coordinates": [[[x, y] for x, y in bbox_poly.exterior.coords]]
    }
    
    try:
        hexagons = h3.polyfill(geo_json, resolution, geo_json_conformant=True)
    except:
        hex_set = set()
        for x in np.linspace(bounds[0], bounds[2], 100):
            for y in np.linspace(bounds[1], bounds[3], 100):
                hex_set.add(h3.geo_to_h3(y, x, resolution))
        hexagons = list(hex_set)
        
    hex_polys = []
    hex_ids = []
    for h in hexagons:
        try:
            boundaries = h3.h3_to_geo_boundary(h, geo_json=True)
            poly = Polygon(boundaries)
            hex_polys.append(poly)
            hex_ids.append(h)
        except Exception as e:
            continue
            
    hex_gdf = gpd.GeoDataFrame({'hex_id': hex_ids}, geometry=hex_polys, crs="EPSG:4326")
    
    # Intersect with the actual study area
    hex_gdf = gpd.sjoin(hex_gdf, gdf[['geometry']], how='inner', predicate='intersects')
    hex_gdf = hex_gdf.drop_duplicates(subset=['hex_id']).reset_index(drop=True)
    hex_gdf = hex_gdf.drop(columns=['index_right'], errors='ignore')
    
    print(f"Generated {len(hex_gdf)} hexes.")
    return hex_gdf

def sample_raster_at_centroids(hex_gdf, raster_path):
    """Sample raster values at hex centroids."""
    if not os.path.exists(raster_path):
        print(f"Warning: Raster not found at {raster_path}. Returning zeros.")
        return np.zeros(len(hex_gdf))
        
    centroids = hex_gdf.geometry.centroid
    coords = [(geom.x, geom.y) for geom in centroids]
    
    try:
        with rasterio.open(raster_path) as src:
            values = list(src.sample(coords))
            values = np.array([v[0] for v in values])
            nodata = src.nodata
            if nodata is not None:
                values = np.where(values == nodata, 0, values)
            values = np.where(values < 0, 0, values)
            return values
    except Exception as e:
        print(f"Error sampling {raster_path}: {e}")
        return np.zeros(len(hex_gdf))

def prepare_data():
    engine = SpatialEngine()
    df_zones = engine.get_zone_spatial_features()
    
    # 1. Create Hex Grid
    hex_gdf = create_h3_grid(df_zones, resolution=7)
    
    # 2. Compute TLU Baseline (Aw)
    ct_aw_val = sample_raster_at_centroids(hex_gdf, "data/6_Ct_2015_Aw.tif")
    sh_aw_val = sample_raster_at_centroids(hex_gdf, "data/6_Sh_2015_Aw.tif")
    gt_aw_val = sample_raster_at_centroids(hex_gdf, "data/6_Gt_2015_Aw.tif")
    
    if np.all(ct_aw_val == 0):
        print("FAO Rasters returning zeros. Fallback to zone-level proxy for prototype.")
        hex_with_zones = gpd.sjoin(hex_gdf, df_zones[['geometry', 'density_proxy']], how='left')
        hex_with_zones = hex_with_zones[~hex_with_zones.index.duplicated(keep='first')]
        base_tlu = hex_with_zones['density_proxy'].fillna(0.1) * 1000 
    else:
        base_tlu = (ct_aw_val * 0.7) + (sh_aw_val * 0.1) + (gt_aw_val * 0.1)
        
    hex_gdf['tlu_aw'] = base_tlu
    
    # 3. Compute Distances
    wp_utm = engine.gdf_waterpoints.to_crs(epsg=32737)
    hex_utm = hex_gdf.to_crs(epsg=32737)
    
    def dist_to_geom(hex_geom, target_gdf):
        if target_gdf.empty: return 10.0
        return target_gdf.distance(hex_geom).min() / 1000.0

    print("Computing distances to water points...")
    hex_gdf['dist_water_km'] = hex_utm.geometry.apply(lambda geom: dist_to_geom(geom, wp_utm))
    
    barrier_path = "data/barrier.geojson"
    if os.path.exists(barrier_path):
        barrier_gdf = gpd.read_file(barrier_path).to_crs(epsg=32737)
        print("Computing distances to barrier...")
        hex_gdf['dist_barrier_km'] = hex_utm.geometry.apply(lambda geom: dist_to_geom(geom, barrier_gdf))
    else:
        print("barrier.geojson not found. Defaulting barrier dist to 10km.")
        hex_gdf['dist_barrier_km'] = 10.0
        
    settlements_utm = engine.gdf_settlements.to_crs(epsg=32737)
    print("Computing distances to settlements...")
    hex_gdf['dist_settlement_km'] = hex_utm.geometry.apply(lambda geom: dist_to_geom(geom, settlements_utm))
    
    if engine.park_union_geom is not None:
        park_utm_series = gpd.GeoSeries([engine.park_union_geom], crs="EPSG:4326").to_crs(epsg=32737)
        print("Computing distances to parks...")
        hex_gdf['dist_park_km'] = hex_utm.geometry.apply(lambda geom: dist_to_geom(geom, park_utm_series))
    else:
        hex_gdf['dist_park_km'] = 10.0

    # 4. Get NDVI/CHIRPS
    hex_with_climate = gpd.sjoin(hex_gdf, df_zones[['geometry', 'ndvi_stress', 'rainfall_deficit', 'name']], how='left')
    hex_with_climate = hex_with_climate[~hex_with_climate.index.duplicated(keep='first')]
    
    hex_gdf['ndvi_stress'] = hex_with_climate['ndvi_stress'].fillna(0.5)
    hex_gdf['rainfall_deficit'] = hex_with_climate['rainfall_deficit'].fillna(0.5)
    hex_gdf['zone_name'] = hex_with_climate['name'].fillna("Unknown")

    # 5. Save Hex GeoDataFrame to Parquet
    os.makedirs("data/parquet", exist_ok=True)
    out_path = "data/parquet/hex_grid.parquet"
    print(f"Writing {len(hex_gdf)} hexes to {out_path}...")
    hex_gdf.to_parquet(out_path)
    print("Done generating base hex grid!")

if __name__ == "__main__":
    prepare_data()
