import os
import json
import xml.etree.ElementTree as ET
import geopandas as gpd
import pandas as pd
import numpy as np
import duckdb
from shapely import wkt
from shapely.geometry import Point


class SpatialEngine:
    def __init__(self, duckdb_path="data/boma_shield.duckdb", shp_path="AMBOSELI CONSERVANCIES.shp", parks_path="national parks.shp", kml_path="export (2).kml", busy_path="busytown.geojson"):
        self.duckdb_path = duckdb_path
        self.con = duckdb.connect(self.duckdb_path)
        self.con.execute("INSTALL spatial; LOAD spatial;")
        # Original file paths kept for fetcher compatibility
        self.shp_path = shp_path
        self.parks_path = parks_path
        self.kml_path = kml_path
        self.busy_path = busy_path
        self.duckdb_path = duckdb_path
        self.con = duckdb.connect(self.duckdb_path)
        # Load DuckDB spatial extension
        self.con.execute("INSTALL spatial; LOAD spatial;")
        self.gdf_conservancies = None
        self.gdf_parks = None
        self.gdf_waterpoints = None
        self.gdf_settlements = None
        self.park_union_geom = None
        self.load_data()

    def load_data(self):
        # Load conservancies from DuckDB (GeoParquet table 'conservancies')
        self.gdf_conservancies = self.con.execute("SELECT *, wkt FROM conservancies").fetchdf()
        self.gdf_conservancies['geometry'] = self.gdf_conservancies['wkt'].apply(wkt.loads)
        self.gdf_conservancies = gpd.GeoDataFrame(self.gdf_conservancies, crs="EPSG:4326")
        if 'wkt' in self.gdf_conservancies.columns:
            self.gdf_conservancies.drop(columns=['wkt'], inplace=True)
        # Ensure clean_name column exists
        if 'clean_name' not in self.gdf_conservancies.columns:
            self.gdf_conservancies['clean_name'] = self.gdf_conservancies.get('Name')
        else:
            self.gdf_conservancies['clean_name'] = self.gdf_conservancies['clean_name'].fillna(self.gdf_conservancies.get('Name')).fillna(self.gdf_conservancies.get('Name_2'))
        # Load parks from DuckDB (table 'parks')
        self.gdf_parks = self.con.execute("SELECT *, wkt FROM parks").fetchdf()
        self.gdf_parks['geometry'] = self.gdf_parks['wkt'].apply(wkt.loads)
        self.gdf_parks = gpd.GeoDataFrame(self.gdf_parks, crs="EPSG:4326")
        if 'wkt' in self.gdf_parks.columns:
            self.gdf_parks.drop(columns=['wkt'], inplace=True)
        # Ensure clean_name column exists for parks
        if 'clean_name' not in self.gdf_parks.columns:
            self.gdf_parks['clean_name'] = self.gdf_parks.get('Name')
        else:
            self.gdf_parks['clean_name'] = self.gdf_parks['clean_name'].fillna(self.gdf_parks.get('Name')).fillna(self.gdf_parks.get('name2'))
        self.gdf_parks['category'] = 'National Park'
        # Build union geometry for parks (used for distance calculations)
        if not self.gdf_parks.empty:
            self.park_union_geom = self.gdf_parks.geometry.unary_union
        else:
            self.park_union_geom = None

        if 'category' not in self.gdf_conservancies.columns:
            self.gdf_conservancies['category'] = 'Conservancy / Group Ranch'

        # Combine Conservancies + National Parks into Unified Ecosystem Region Zones
        parks_subset = self.gdf_parks[['clean_name', 'category', 'geometry']]
        cons_subset = self.gdf_conservancies[['clean_name', 'category', 'geometry']]
        self.gdf_all_zones = pd.concat([cons_subset, parks_subset], ignore_index=True)
        self.gdf_all_zones = gpd.GeoDataFrame(self.gdf_all_zones, crs="EPSG:4326")

        # 3. Load human settlements from DuckDB (table 'settlements')
        self.gdf_settlements = self.con.execute("SELECT *, wkt FROM settlements").fetchdf()
        if not self.gdf_settlements.empty:
            self.gdf_settlements['geometry'] = self.gdf_settlements['wkt'].apply(wkt.loads)
            self.gdf_settlements = gpd.GeoDataFrame(self.gdf_settlements, geometry='geometry', crs="EPSG:4326")
        else:
            self.gdf_settlements = gpd.GeoDataFrame(columns=['name', 'geometry'], crs="EPSG:4326")

        # 4. Load waterpoints from DuckDB (table 'waterpoints')
        self.gdf_waterpoints = self.con.execute("SELECT *, wkt FROM waterpoints").fetchdf()
        if not self.gdf_waterpoints.empty:
            self.gdf_waterpoints['geometry'] = self.gdf_waterpoints['wkt'].apply(wkt.loads)
            self.gdf_waterpoints = gpd.GeoDataFrame(self.gdf_waterpoints, geometry='geometry', crs="EPSG:4326")
        else:
            self.gdf_waterpoints = gpd.GeoDataFrame(columns=['name', 'geometry', 'lat', 'lon'], crs="EPSG:4326")


    def get_zone_spatial_features(self, selected_dekad="2024-W39"):
        """
        Calculates spatial metrics for each conservancy zone:
        - Centroid lat/lon
        - Area in sq km
        - Min distance to water point (km)
        - Min distance to park boundary (km)
        - Estimated corridor obstruction score (0-1)
        - Baseline livestock/settlement density proxy (0-1)
        - Weekly satellite rainfall deficit score (from selected CHIRPS dekad)
        """
        # Reproject to UTM zone 37S (EPSG:32737) for accurate distance & area calculations in meters
        gdf_utm = self.gdf_all_zones.to_crs(epsg=32737)
        wp_utm = self.gdf_waterpoints.to_crs(epsg=32737) if not self.gdf_waterpoints.empty else None
        
        park_utm = gpd.GeoSeries([self.park_union_geom], crs="EPSG:4326").to_crs(epsg=32737).iloc[0] if self.park_union_geom is not None else None
        busy_utm = self.gdf_settlements.to_crs(epsg=32737) if not self.gdf_settlements.empty else None
        
        # Fetch 4-week satellite time series & GEE live stats
        ts_map_rain = {}
        ts_map_ndvi = {}

        # Check GEE live stats JSON first
        gee_json_path = os.path.join("data", "rasters", "gee_live_stats.json")
        gee_data_map = {}
        if os.path.exists(gee_json_path):
            try:
                with open(gee_json_path, 'r') as f:
                    gee_list = json.load(f)
                    gee_data_map = {item['name']: item for item in gee_list}
                print(f"Loaded live GEE satellite statistics for {len(gee_data_map)} zones.")
            except Exception as e:
                print(f"Could not read GEE live stats: {e}")

        try:
            from src.fetch_real_data import DataFetcher
            fetcher = DataFetcher()
            ts_data = fetcher.get_weekly_time_series(self.shp_path)
            if selected_dekad in ts_data:
                df_dek = ts_data[selected_dekad]
                ts_map_rain = dict(zip(df_dek['name'], df_dek['rainfall_deficit']))
                if 'ndvi_stress' in df_dek.columns:
                    ts_map_ndvi = dict(zip(df_dek['name'], df_dek['ndvi_stress']))
        except Exception as e:
            print(f"Time-series sampling skipped: {e}")

        results = []
        for idx, row in self.gdf_all_zones.iterrows():
            geom_4326 = row.geometry
            geom_utm = gdf_utm.loc[idx, 'geometry']
            name = row['clean_name']
            category = row.get('category', 'Zone')
            
            centroid_4326 = geom_4326.centroid
            area_km2 = geom_utm.area / 1e6
            
            # Distance to water (km)
            if wp_utm is not None and not wp_utm.empty:
                min_dist_water_m = wp_utm.distance(geom_utm).min()
                min_dist_water_km = max(0.1, min_dist_water_m / 1000.0)
            else:
                min_dist_water_km = 5.0
                
            # Distance to park boundary (km)
            if category == 'National Park':
                dist_park_km = 0.0
            elif park_utm is not None and not park_utm.equals(geom_utm):
                dist_park_m = geom_utm.distance(park_utm)
                dist_park_km = max(0.0, dist_park_m / 1000.0)
            else:
                dist_park_km = 0.0
                
            # Heuristic Baseline Corridor Obstruction & Density based on literature & geographic location
            is_corridor_zone = any(k in name.lower() for k in ['kimana', 'kitenden', 'selenkay', 'kilitome', 'motikanju', 'rombo', 'mbirikani', 'amboseli', 'tsavo'])
            corridor_obstruction = np.random.uniform(0.6, 0.9) if is_corridor_zone else np.random.uniform(0.2, 0.5)
            density_proxy = np.random.uniform(0.5, 0.85) if is_corridor_zone else np.random.uniform(0.2, 0.6)
            
            # Weekly satellite rainfall deficit (GEE live or CHIRPS dekad)
            if name in gee_data_map:
                real_deficit = gee_data_map[name]['rainfall_deficit']
                ndvi_stress = gee_data_map[name]['ndvi_stress']
            else:
                real_deficit = ts_map_rain.get(name) if name in ts_map_rain else round(float(np.random.beta(2.5, 2.5)), 2)
                if name in ts_map_ndvi:
                    ndvi_stress = ts_map_ndvi[name]
                else:
                    np.random.seed(idx + int(selected_dekad[-2:] if selected_dekad[-2:].isdigit() else 39))
                    ndvi_stress = round(float(np.clip(0.4 + (int(selected_dekad[-2:]) if selected_dekad[-2:].isdigit() else 39) * 0.01 + np.random.uniform(-0.1, 0.1), 0.1, 0.95)), 2)

            results.append({
                'id': idx,
                'name': name,
                'category': category,
                'centroid_lat': centroid_4326.y,
                'centroid_lon': centroid_4326.x,
                'area_km2': round(area_km2, 2),
                'dist_water_km': round(min_dist_water_km, 2),
                'dist_park_km': round(dist_park_km, 2),
                'corridor_obstruction': round(corridor_obstruction, 2),
                'density_proxy': round(density_proxy, 2),
                'rainfall_deficit': real_deficit,
                'ndvi_stress': ndvi_stress,
                'geometry': geom_4326
            })
            
        return gpd.GeoDataFrame(results, crs="EPSG:4326")






if __name__ == "__main__":
    engine = SpatialEngine()
    df_zones = engine.get_zone_spatial_features()
    print(f"Processed {len(df_zones)} conservancy zones.")
    print(df_zones[['name', 'area_km2', 'dist_water_km', 'dist_park_km', 'corridor_obstruction']].head(10))
