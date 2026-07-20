import geopandas as gpd
import xml.etree.ElementTree as ET
import pandas as pd

print("=== SHAPEFILE ===")
try:
    gdf = gpd.read_file("AMBOSELI CONSERVANCIES.shp")
    print(f"CRS: {gdf.crs}")
    print(f"Count: {len(gdf)}")
    print(f"Columns: {list(gdf.columns)}")
    for idx, row in gdf.iterrows():
        dict_row = dict(row)
        del dict_row['geometry']
        print(f"Row {idx}: {dict_row}")
except Exception as e:
    print(f"Error reading shapefile: {e}")

print("\n=== KML WATERPOINTS ===")
try:
    tree = ET.parse("export (2).kml")
    root = tree.getroot()
    # Find all Placemarks
    placemarks = root.findall('.//{http://www.opengis.net/kml/2.2}Placemark')
    if not placemarks:
        placemarks = root.findall('.//Placemark')
    
    print(f"Placemarks count in KML: {len(placemarks)}")
    wp_list = []
    for pm in placemarks:
        name_el = pm.find('{http://www.opengis.net/kml/2.2}name')
        if name_el is None:
            name_el = pm.find('name')
        coord_el = pm.find('.//{http://www.opengis.net/kml/2.2}coordinates')
        if coord_el is None:
            coord_el = pm.find('.//coordinates')
            
        name = name_el.text.strip() if name_el is not None and name_el.text else "Unnamed"
        coords_str = coord_el.text.strip() if coord_el is not None and coord_el.text else ""
        if coords_str:
            tokens = coords_str.replace(',', ' ').split()
            if len(tokens) >= 2:
                try:
                    lon, lat = float(tokens[0]), float(tokens[1])
                    wp_list.append({'name': name, 'lat': lat, 'lon': lon})
                except ValueError:
                    pass
    
    df_wp = pd.DataFrame(wp_list)
    print(f"Extracted {len(df_wp)} water points.")
    print(df_wp.head(10))
except Exception as e:
    print(f"Error parsing KML: {e}")

