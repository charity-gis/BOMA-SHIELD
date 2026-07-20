import os
import gzip
import shutil
import urllib.request
import numpy as np
import geopandas as gpd
import pandas as pd

class DataFetcher:
    # CHIRPS Dekad Time-Series (4 recent Dekads / ~1 Month of 10-day updates)
    DEKADS = [
        {"id": "2024-W36", "label": "Dekad 1 (Aug 21-31)", "url": "https://data.chc.ucsb.edu/products/CHIRPS-2.0/africa_dekad/tifs/chirps-v2.0.2024.08.3.tif.gz", "file": "chirps_2024_08_3.tif"},
        {"id": "2024-W37", "label": "Dekad 2 (Sep 01-10)", "url": "https://data.chc.ucsb.edu/products/CHIRPS-2.0/africa_dekad/tifs/chirps-v2.0.2024.09.1.tif.gz", "file": "chirps_2024_09_1.tif"},
        {"id": "2024-W38", "label": "Dekad 3 (Sep 11-20)", "url": "https://data.chc.ucsb.edu/products/CHIRPS-2.0/africa_dekad/tifs/chirps-v2.0.2024.09.2.tif.gz", "file": "chirps_2024_09_2.tif"},
        {"id": "2024-W39", "label": "Dekad 4 (Sep 21-30)", "url": "https://data.chc.ucsb.edu/products/CHIRPS-2.0/africa_dekad/tifs/chirps-v2.0.2024.09.3.tif.gz", "file": "chirps_2024_09_3.tif"}
    ]
    
    def __init__(self, output_dir="data/rasters"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def fetch_dekad(self, dekad_info):
        """
        Downloads a specific CHIRPS dekad GeoTIFF if not already present locally.
        """
        gz_path = os.path.join(self.output_dir, dekad_info["file"] + ".gz")
        tif_path = os.path.join(self.output_dir, dekad_info["file"])

        if not os.path.exists(tif_path):
            print(f"Downloading CHIRPS dekad {dekad_info['id']} from {dekad_info['url']}...")
            try:
                urllib.request.urlretrieve(dekad_info["url"], gz_path)
                with gzip.open(gz_path, 'rb') as f_in:
                    with open(tif_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                os.remove(gz_path)
                print(f"Saved {dekad_info['id']} to {tif_path}")
            except Exception as e:
                print(f"Error downloading {dekad_info['id']}: {e}")
                return None
        return tif_path

    def sample_ndvi_stats(self, shapefile_path="AMBOSELI CONSERVANCIES.shp"):
        """
        Samples real NDVI vegetation index values per conservancy polygon from any local GeoTIFF raster
        in data/rasters/ (e.g. ndvi_sept2024.tif or modis_ndvi.tif).
        Converts mean NDVI (-1.0 to 1.0) to NDVI Stress Score (0.0 = green/healthy, 1.0 = severe drought stress).
        """
        try:
            from rasterstats import zonal_stats
        except ImportError:
            return {}

        # Look for local NDVI rasters in data/rasters
        ndvi_files = [f for f in os.listdir(self.output_dir) if "ndvi" in f.lower() and f.endswith(('.tif', '.tiff'))]
        if not ndvi_files:
            return {}

        tif_path = os.path.join(self.output_dir, ndvi_files[0])
        gdf = gpd.read_file(shapefile_path)

        try:
            print(f"Computing NDVI zonal statistics against {tif_path}...")
            stats = zonal_stats(shapefile_path, tif_path, stats=["mean"])
            mean_ndvis = []
            for s in stats:
                val = s['mean']
                # Handles scaled NDVI (e.g., MODIS 0-10000 or raw -1.0 to 1.0)
                if val is not None:
                    if val > 1.0:
                        val = val / 10000.0  # Scale down MODIS integer scale
                    mean_ndvis.append(val)
                else:
                    mean_ndvis.append(0.25)
            
            # Convert NDVI to Stress Score (0.0 to 1.0)
            stress_scores = [round(float(np.clip(1.0 - (v / 0.6), 0.0, 1.0)), 2) for v in mean_ndvis]
            
            return dict(zip(gdf['Name'].fillna(gdf['Name_2']), stress_scores))
        except Exception as e:
            print(f"Error sampling NDVI stats: {e}")
            return {}

    def get_weekly_time_series(self, shapefile_path="AMBOSELI CONSERVANCIES.shp"):
        """
        Calculates 4-week time-series zonal statistics per conservancy polygon.
        Returns a dictionary mapping dekad_id -> DataFrame of zonal stats.
        """
        try:
            from rasterstats import zonal_stats
        except ImportError:
            print("rasterstats not installed.")
            return {}

        gdf = gpd.read_file(shapefile_path)
        time_series_data = {}
        ndvi_stress_map = self.sample_ndvi_stats(shapefile_path)

        for dek in self.DEKADS:
            tif_path = self.fetch_dekad(dek)
            if tif_path and os.path.exists(tif_path):
                try:
                    stats = zonal_stats(shapefile_path, tif_path, stats=["mean"])
                    mean_rain = [s['mean'] if s['mean'] is not None else 5.0 for s in stats]
                    max_r = max(mean_rain) if max(mean_rain) > 0 else 50.0
                    deficits = [round(float(np.clip(1.0 - (r / max_r), 0.0, 1.0)), 2) for r in mean_rain]
                    
                    names = gdf['Name'].fillna(gdf['Name_2'])
                    # If real NDVI raster sampled, use real NDVI stress, else dekad-based NDVI trend
                    ndvi_list = [ndvi_stress_map.get(n, 0.5) for n in names] if ndvi_stress_map else None

                    df_dek = pd.DataFrame({
                        'name': names,
                        'rain_mm': [round(r, 2) for r in mean_rain],
                        'rainfall_deficit': deficits
                    })
                    if ndvi_list:
                        df_dek['ndvi_stress'] = ndvi_list

                    time_series_data[dek['id']] = df_dek
                except Exception as e:
                    print(f"Error computing stats for {dek['id']}: {e}")

        return time_series_data


if __name__ == "__main__":
    fetcher = DataFetcher()
    ts = fetcher.get_weekly_time_series()
    print(f"Processed time-series for {len(ts)} dekads.")
