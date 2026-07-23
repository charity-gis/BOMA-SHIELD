import os
import geopandas as gpd
import duckdb
from shapely import wkt
from shapely.geometry import Point
import xml.etree.ElementTree as ET

# Ensure directories exist
PARQUET_DIR = os.path.join('data', 'parquet')
os.makedirs(PARQUET_DIR, exist_ok=True)

DUCKDB_PATH = os.path.join('data', 'boma_shield.duckdb')

def _load_duckdb():
    con = duckdb.connect(DUCKDB_PATH)
    con.execute("INSTALL spatial; LOAD spatial;")
    return con

def import_layer(gdf: gpd.GeoDataFrame, table_name: str, con=None):
    """Write a GeoDataFrame to GeoParquet and import it into DuckDB as *table_name*.
    Geometry is stored as WKT to avoid requiring the DuckDB spatial extension.
    Existing table will be replaced.
    """
    if con is None:
        con = _load_duckdb()
    # Write GeoDataFrame to Parquet (including WKT column)
    gdf = gdf.copy()
    
    # Ensure EPSG:4326
    if gdf.crs is not None and gdf.crs.to_epsg() != 4326:
        print(f"Reprojecting {table_name} from {gdf.crs} to EPSG:4326")
        gdf = gdf.to_crs(epsg=4326)
    elif gdf.crs is None:
        print(f"Warning: {table_name} has no CRS. Assuming EPSG:4326")
        gdf = gdf.set_crs(epsg=4326)
        
    # Convert geometry to WKT string for storage
    gdf['wkt'] = gdf.geometry.apply(lambda geom: geom.wkt if geom else None)
    # Drop shapely geometry objects (they are not serializable)
    gdf = gdf.drop(columns=['geometry'])
    parquet_path = os.path.join(PARQUET_DIR, f"{table_name}.parquet")
    gdf.to_parquet(parquet_path, engine='pyarrow')
    # Load into DuckDB – replace if exists; keep wkt column only (no geometry conversion)
    con.execute(f"DROP TABLE IF EXISTS {table_name}")
    con.execute(f"CREATE TABLE {table_name} AS SELECT * FROM read_parquet('{parquet_path}')")
    con.commit()
    print(f"[+] Imported {table_name} into DuckDB from {parquet_path}")
    return con

def import_shapefile(shp_path: str, table_name: str, con=None):
    gdf = gpd.read_file(shp_path)
    return import_layer(gdf, table_name, con)

def import_geojson(geojson_path: str, table_name: str, con=None):
    gdf = gpd.read_file(geojson_path)
    return import_layer(gdf, table_name, con)

def import_kml(kml_path: str, table_name: str, con=None):
    """Import a KML file.
    Tries to read using GeoPandas (requires GDAL KML driver). If that fails,
    falls back to manual XML parsing to extract point placemarks.
    """
    try:
        gdf = gpd.read_file(kml_path, driver='KML')
    except Exception:
        # Manual fallback parsing
        wp_list = []
        tree = ET.parse(kml_path)
        root = tree.getroot()
        placemarks = root.findall('.//{http://www.opengis.net/kml/2.2}Placemark')
        if not placemarks:
            placemarks = root.findall('.//Placemark')
        for pm in placemarks:
            name_el = pm.find('{http://www.opengis.net/kml/2.2}name') or pm.find('name')
            coord_el = pm.find('.//{http://www.opengis.net/kml/2.2}coordinates') or pm.find('.//coordinates')
            name = name_el.text.strip() if name_el is not None and name_el.text else "Water Point"
            coords_str = coord_el.text.strip() if coord_el is not None and coord_el.text else ""
            if coords_str:
                tokens = coords_str.replace(',', ' ').split()
                if len(tokens) >= 2:
                    try:
                        lon, lat = float(tokens[0]), float(tokens[1])
                        wp_list.append({"name": name, "geometry": Point(lon, lat), "lat": lat, "lon": lon})
                    except ValueError:
                        pass
        if wp_list:
            gdf = gpd.GeoDataFrame(wp_list, crs="EPSG:4326", geometry='geometry')
        else:
            gdf = gpd.GeoDataFrame(columns=['name', 'lat', 'lon', 'geometry'], crs="EPSG:4326")
            gdf.set_geometry('geometry', inplace=True)
    return import_layer(gdf, table_name, con)

if __name__ == "__main__":
    con = _load_duckdb()
    # Import known layers – relative paths
    import_shapefile('AMBOSELI CONSERVANCIES.shp', 'conservancies', con)
    import_shapefile('Amboseli_Ranches/Ranch boundaries.shp', 'group_ranches', con)
    import_shapefile('national parks.shp', 'parks', con)
    import_geojson('busytown.geojson', 'settlements', con)
    import_kml('export (2).kml', 'waterpoints', con)
    con.close()
    print("[+] All layers imported into DuckDB.")
