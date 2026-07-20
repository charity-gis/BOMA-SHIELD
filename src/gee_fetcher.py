import os
import json
import geopandas as gpd
import pandas as pd
import datetime

class GEEFetcher:
    """
    Google Earth Engine (GEE) Data Fetcher for Boma Shield.
    Fetches real-time Sentinel-2 / MODIS NDVI and CHIRPS rainfall
    directly for each conservancy polygon in AMBOSELI CONSERVANCIES.shp.
    """
    def __init__(self, shapefile_path="AMBOSELI CONSERVANCIES.shp"):
        self.shapefile_path = shapefile_path
        self.ee_initialized = False

    def init_gee(self, project_id=None):
        """
        Initializes Google Earth Engine API with Google Cloud Project ID.
        Prompts authentication if not already authenticated.
        """
        config_file = os.path.join("data", "gee_config.json")
        if not project_id and os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    cfg = json.load(f)
                    project_id = cfg.get("project_id")
            except Exception:
                pass

        project = project_id or os.getenv("EE_PROJECT_ID") or "ee-boma-shield"
        try:
            import ee
            try:
                ee.Initialize(project=project)
                self.ee_initialized = True
                print(f"[+] Google Earth Engine initialized successfully with project: '{project}'.")
            except Exception as e:
                print(f"[*] Initializing GEE with project '{project}' failed ({e}). Attempting authentication...")
                ee.Authenticate()
                ee.Initialize(project=project)
                self.ee_initialized = True
                print(f"[+] Google Earth Engine authenticated and initialized with project '{project}'.")
        except Exception as e:
            print(f"[-] Could not initialize GEE: {e}")
            print("\n[!] GEE Setup Hint: Run 'python authenticate_gee.py' to authorize GEE with your Google Cloud Project ID.")
            self.ee_initialized = False
        return self.ee_initialized

    def fetch_live_gee_stats(self, days_back=30, output_json="data/rasters/gee_live_stats.json"):
        """
        Queries GEE for Sentinel-2 10m NDVI and CHIRPS rainfall over the last N days
        per conservancy polygon in AMBOSELI CONSERVANCIES.shp.
        """
        if not self.ee_initialized and not self.init_gee():
            return None

        import ee
        print(f"[*] Querying Google Earth Engine over last {days_back} days...")
        
        gdf = gpd.read_file(self.shapefile_path)
        gdf_4326 = gdf.to_crs(epsg=4326)

        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=days_back)
        
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        # 1. CHIRPS Daily Rainfall Collection
        chirps = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY') \
                   .filterDate(start_str, end_str) \
                   .sum() \
                   .select('precipitation')

        # 2. Sentinel-2 Surface Reflectance (Cloud-masked 10m NDVI)
        def mask_s2_clouds(image):
            qa = image.select('QA60')
            cloudBitMask = 1 << 10
            cirrusBitMask = 1 << 11
            mask = qa.bitwiseAnd(cloudBitMask).eq(0).And(qa.bitwiseAnd(cirrusBitMask).eq(0))
            return image.updateMask(mask).divide(10000)

        s2_collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
                          .filterDate(start_str, end_str) \
                          .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30)) \
                          .map(mask_s2_clouds)

        # Compute Median Composite NDVI: (NIR - RED) / (NIR + RED) -> (B8 - B4) / (B8 + B4)
        s2_ndvi = s2_collection.median().normalizedDifference(['B8', 'B4']).rename('ndvi')

        results = []
        for idx, row in gdf_4326.iterrows():
            name = row.get('Name') or row.get('Name_2') or f"Zone_{idx}"
            geom_json = row.geometry.__geo_interface__
            ee_geom = ee.Geometry(geom_json)

            # Reduce Region for CHIRPS rainfall (sum mm)
            chirps_stat = chirps.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=ee_geom,
                scale=5000,
                maxPixels=1e8
            ).getInfo()
            
            # Reduce Region for Sentinel-2 NDVI (mean index -1 to 1)
            ndvi_stat = s2_ndvi.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=ee_geom,
                scale=20,
                maxPixels=1e8
            ).getInfo()

            rain_val = chirps_stat.get('precipitation', 10.0) or 10.0
            ndvi_val = ndvi_stat.get('ndvi', 0.25) or 0.25

            # Calculate Deficit and Stress Scores (0-1)
            rain_deficit = round(float(max(0.0, min(1.0, 1.0 - (rain_val / 60.0)))), 2)
            ndvi_stress = round(float(max(0.0, min(1.0, 1.0 - (ndvi_val / 0.6)))), 2)

            results.append({
                'name': name,
                'gee_rain_mm': round(float(rain_val), 2),
                'gee_ndvi_raw': round(float(ndvi_val), 3),
                'rainfall_deficit': rain_deficit,
                'ndvi_stress': ndvi_stress
            })

        os.makedirs(os.path.dirname(output_json), exist_ok=True)
        with open(output_json, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"[+] GEE satellite statistics saved to {output_json}")
        return results

if __name__ == "__main__":
    fetcher = GEEFetcher()
    fetcher.fetch_live_gee_stats()

