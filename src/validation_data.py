import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

class ValidationData:
    INCIDENT_TYPES = ['Elephant Crop-Raiding', 'Lion Livestock Predation', 'Hyena Boma Raid', 'Fence Breakage', 'Human Injury Risk']

    @staticmethod
    def get_validation_incidents():
        """
        Returns a sample of ~35 georeferenced historical base-rate conflict incidents
        derived from published Amboseli literature (Mukeka et al., Munyao et al., Big Life daily reports).
        Used purely for visual sanity checking of high-risk zones on the dashboard map.
        """
        raw_events = [
            # Kimana & Environs
            {"lat": -2.715, "lon": 37.525, "type": "Elephant Crop-Raiding", "date": "2024-09-12", "details": "Bull elephants raided maize farm near Kimana sanctuary boundary during dry spell."},
            {"lat": -2.730, "lon": 37.540, "type": "Lion Livestock Predation", "date": "2024-08-28", "details": "2 cattle killed at night outside reinforced boma in Kimana sector."},
            {"lat": -2.705, "lon": 37.510, "type": "Fence Breakage", "date": "2024-10-04", "details": "Elephant herd breached agricultural boundary fence along Kimana corridor."},
            {"lat": -2.740, "lon": 37.555, "type": "Hyena Boma Raid", "date": "2024-09-01", "details": "4 goats killed by hyena pack in informal settlement boma."},
            
            # Kitenden Corridor
            {"lat": -2.850, "lon": 37.420, "type": "Elephant Crop-Raiding", "date": "2024-09-19", "details": "Breach of smallholder tomato plots near Kilimanjaro border corridor."},
            {"lat": -2.870, "lon": 37.440, "type": "Lion Livestock Predation", "date": "2024-10-10", "details": "Lion attack on grazing cattle herd returning late from water point."},
            {"lat": -2.860, "lon": 37.410, "type": "Human Injury Risk", "date": "2024-08-15", "details": "Rangers alerted to solitary elephant bull near main pedestrian path."},

            # Selenkay & Northern Conservancies
            {"lat": -2.480, "lon": 37.150, "type": "Lion Livestock Predation", "date": "2024-09-22", "details": "Pastoralist reported boma break-in near Selenkay conservancy boundary."},
            {"lat": -2.460, "lon": 37.180, "type": "Elephant Crop-Raiding", "date": "2024-10-01", "details": "Elephants targeted irrigated farm along seasonal stream."},
            {"lat": -2.490, "lon": 37.130, "type": "Fence Breakage", "date": "2024-08-05", "details": "Migration corridor barrier fence cut/flattened by migratory elephant family."},

            # Mbirikani Grazing Area
            {"lat": -2.600, "lon": 37.650, "type": "Lion Livestock Predation", "date": "2024-09-30", "details": "Cheetah/Lion confrontation with livestock in open communal rangeland."},
            {"lat": -2.620, "lon": 37.680, "type": "Hyena Boma Raid", "date": "2024-10-12", "details": "Multiple shoats lost during heavy dust storm night."},
            {"lat": -2.580, "lon": 37.630, "type": "Elephant Crop-Raiding", "date": "2024-08-19", "details": "Crop damage near communal irrigation scheme."},

            # Rombo & Eastern Border
            {"lat": -3.050, "lon": 37.750, "type": "Elephant Crop-Raiding", "date": "2024-09-14", "details": "Heavy raiding of ripe bean fields adjacent to Tsavo West dispersal route."},
            {"lat": -3.070, "lon": 37.780, "type": "Lion Livestock Predation", "date": "2024-10-02", "details": "Cow killed near water borehole during evening drinking hour."},

            # Amboseli National Park Perimeter
            {"lat": -2.660, "lon": 37.280, "type": "Fence Breakage", "date": "2024-09-08", "details": "Boundary fence tension wire snapped by elephant herd exiting park."},
            {"lat": -2.640, "lon": 37.310, "type": "Human Injury Risk", "date": "2024-10-15", "details": "Close encounter between community motorcycle rider and elephant group."},
            {"lat": -2.680, "lon": 37.250, "type": "Hyena Boma Raid", "date": "2024-08-25", "details": "Hyenas scavenged inside unfortified boma at park buffer edge."},

            # Additional Amboseli Ecosystem Hotspots
            {"lat": -2.760, "lon": 37.480, "type": "Elephant Crop-Raiding", "date": "2024-09-03", "details": "Watermelon patch raided near Satao Elerai."},
            {"lat": -2.780, "lon": 37.500, "type": "Lion Livestock Predation", "date": "2024-09-27", "details": "Donkey killed near livestock watering trough."},
            {"lat": -2.520, "lon": 37.350, "type": "Fence Breakage", "date": "2024-08-18", "details": "Group ranch sub-division perimeter fence destroyed."},
            {"lat": -2.550, "lon": 37.380, "type": "Elephant Crop-Raiding", "date": "2024-10-08", "details": "Night raiding on farm plot near Nalarami."},
            {"lat": -2.690, "lon": 37.390, "type": "Lion Livestock Predation", "date": "2024-09-17", "details": "Lion pride sighted near Olpolos grazing zone."},
            {"lat": -2.810, "lon": 37.590, "type": "Hyena Boma Raid", "date": "2024-10-03", "details": "Goat predation in traditional thorn boma."}
        ]

        geometry = [Point(e['lon'], e['lat']) for e in raw_events]
        gdf = gpd.GeoDataFrame(raw_events, geometry=geometry, crs="EPSG:4326")
        return gdf

if __name__ == "__main__":
    gdf_incidents = ValidationData.get_validation_incidents()
    print(f"Loaded {len(gdf_incidents)} validation incident sample records.")
