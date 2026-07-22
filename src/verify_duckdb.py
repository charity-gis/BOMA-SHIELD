import os, sys
sys.path.append(os.path.abspath('.'))
from src.spatial_engine import SpatialEngine

if __name__ == "__main__":
    engine = SpatialEngine()
    df = engine.get_zone_spatial_features(selected_dekad="2024-W39")
    print("Loaded zones (first 5 rows):")
    print(df[['name', 'risk_score', 'risk_level']].head())


if __name__ == "__main__":
    engine = SpatialEngine()
    df = engine.get_zone_spatial_features(selected_dekad="2024-W39")
    print("Loaded zones (first 5 rows):")
    print(df[['name', 'risk_score', 'risk_level']].head())
