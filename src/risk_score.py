import pandas as pd
import numpy as np
import geopandas as gpd

def normalize(series):
    """Min-Max normalize a series to [0, 1]. Returns zeros if all identical."""
    s_min, s_max = series.min(), series.max()
    if s_min == s_max:
        return np.zeros_like(series)
    return (series - s_min) / (s_max - s_min)

def compute_exposure(hex_gdf, season=0.5):
    """
    Computes Da (Dasymetric) and Aw (Areal-Weighted) exposure using TLU.
    
    season: 0 (Peak Dry) to 1 (Peak Wet).
    In Dry season, livestock is tightly clustered around water and good vegetation.
    In Wet season, livestock can spread out more evenly.
    """
    # Baseline Areal-Weighted Exposure (uniform spread of census data)
    exposure_aw = hex_gdf['tlu_aw'].copy()
    
    # Interaction terms for redistribution
    # dry season (season -> 0) means higher weight on water and vegetation
    # wet season (season -> 1) means lower weight (more uniform)
    season_intensity = 1.0 + (1.0 - season) # 1.0 in wet, 2.0 in dry
    
    # We want livestock to prefer lower NDVI stress and lower distance to water.
    # ndvi_stress is [0, 1] (higher = more stress/worse vegetation)
    # dist_water_km is positive, higher is worse.
    
    max_water = hex_gdf['dist_water_km'].max()
    if max_water == 0: max_water = 1.0
    norm_water_dist = hex_gdf['dist_water_km'] / max_water
    
    # Weight formula: Higher score = more attractive to livestock
    # Score = (1 - ndvi_stress) + (1 - norm_water_dist)
    attr_score = (1.0 - hex_gdf['ndvi_stress']) + (1.0 - norm_water_dist)
    
    # Apply season as an exponent to increase contrast in dry season
    da_weights = np.power(attr_score, season_intensity)
    
    # Apply land_tenure flat modifier (e.g. 1.2x for group ranches)
    if 'land_tenure' in hex_gdf.columns:
        # Increase weight slightly for group ranches to reflect managed grazing concentration
        da_weights = np.where(hex_gdf['land_tenure'] == 'group_ranch', da_weights * 1.2, da_weights)
    
    # Redistribute TLU within each zone based on weights
    hex_gdf['da_weight'] = da_weights
    
    exposure_da = np.zeros_like(exposure_aw)
    
    for zone in hex_gdf['zone_name'].unique():
        mask = hex_gdf['zone_name'] == zone
        zone_total_tlu = hex_gdf.loc[mask, 'tlu_aw'].sum()
        zone_weight_sum = hex_gdf.loc[mask, 'da_weight'].sum()
        
        if zone_weight_sum > 0:
            exposure_da[mask] = (hex_gdf.loc[mask, 'da_weight'] / zone_weight_sum) * zone_total_tlu
        else:
            exposure_da[mask] = hex_gdf.loc[mask, 'tlu_aw']
            
    hex_gdf['exposure_aw'] = exposure_aw
    hex_gdf['exposure_da'] = exposure_da
    
    hex_gdf['norm_exposure_aw'] = normalize(exposure_aw)
    hex_gdf['norm_exposure_da'] = normalize(exposure_da)
    
    return hex_gdf

def compute_hazard(hex_gdf, weights, season=0.5):
    """
    Computes Hazard independently of livestock exposure covariates.
    Excludes: NDVI, CHIRPS, Water Distance.
    Includes: Barrier Distance, Settlement Distance, Season.
    """
    # 1. Distance to Park/Barrier (Closer = Higher Hazard)
    max_barrier = hex_gdf['dist_barrier_km'].max()
    if max_barrier == 0: max_barrier = 1.0
    hazard_barrier = 1.0 - (hex_gdf['dist_barrier_km'] / max_barrier)
    
    # 2. Distance to Settlements (Closer = Higher Hazard for HWC usually)
    max_settle = hex_gdf['dist_settlement_km'].max()
    if max_settle == 0: max_settle = 1.0
    hazard_settle = 1.0 - (hex_gdf['dist_settlement_km'] / max_settle)
    
    # 3. Seasonal wildlife/conflict term (independent of livestock)
    # E.g., Dry season (season -> 0) pushes wildlife out of parks seeking resources, increasing hazard globally
    season_hazard = (1.0 - season) 
    
    w_barrier = weights.get('boundary_proximity', 0.5)
    w_settle = weights.get('settlement_proximity', 0.3)
    w_season = weights.get('season_hazard', 0.2)
    
    total_w = w_barrier + w_settle + w_season
    w_b, w_s, w_seas = w_barrier/total_w, w_settle/total_w, w_season/total_w
    
    raw_hazard = (hazard_barrier * w_b) + (hazard_settle * w_s) + (season_hazard * w_seas)
    
    # Apply mitigation_score multiplier (e.g., presence of scouts or compensation)
    if 'mitigation_score' in hex_gdf.columns:
        raw_hazard = raw_hazard * hex_gdf['mitigation_score']
    
    hex_gdf['hazard_score'] = normalize(raw_hazard)
    return hex_gdf

def compute_risk(hex_gdf):
    """Risk = Exposure x Hazard (Multiplicative)"""
    hex_gdf['risk_da'] = normalize(hex_gdf['norm_exposure_da'] * hex_gdf['hazard_score'])
    hex_gdf['risk_aw'] = normalize(hex_gdf['norm_exposure_aw'] * hex_gdf['hazard_score'])
    
    # Discretize risk
    hex_gdf['risk_level_da'] = pd.cut(hex_gdf['risk_da'], bins=[-0.1, 0.33, 0.66, 1.1], labels=['LOW', 'MEDIUM', 'HIGH'])
    hex_gdf['risk_level_aw'] = pd.cut(hex_gdf['risk_aw'], bins=[-0.1, 0.33, 0.66, 1.1], labels=['LOW', 'MEDIUM', 'HIGH'])
    return hex_gdf

def compare_da_vs_aw(hex_gdf):
    """
    Computes spatial correlation and flags high divergence areas.
    Returns: correlation_coeff, hex_gdf_with_divergence
    """
    # Pearson correlation
    if hex_gdf['risk_da'].std() == 0 or hex_gdf['risk_aw'].std() == 0:
        corr = 1.0
    else:
        corr = hex_gdf['risk_da'].corr(hex_gdf['risk_aw'])
        
    # Divergence absolute difference
    hex_gdf['divergence'] = np.abs(hex_gdf['risk_da'] - hex_gdf['risk_aw'])
    
    # Stratified Divergence Report
    if 'land_tenure' in hex_gdf.columns:
        print("--- Divergence Stratified by Land Tenure ---")
        stratified = hex_gdf.groupby('land_tenure')['divergence'].mean()
        print(stratified)
        print("--------------------------------------------")
    
    return corr, hex_gdf

def run_pipeline(hex_gdf, weights, season=0.5):
    hex_gdf = compute_exposure(hex_gdf, season)
    hex_gdf = compute_hazard(hex_gdf, weights, season)
    hex_gdf = compute_risk(hex_gdf)
    corr, hex_gdf = compare_da_vs_aw(hex_gdf)
    return hex_gdf, corr

def rollup_to_polygons(hex_gdf, poly_gdf):
    """Aggregates hex risk scores up to operational polygons (e.g. conservancies)."""
    # Spatial join hex centroids to polygons
    hex_centroids = hex_gdf.copy()
    hex_centroids['geometry'] = hex_centroids.geometry.centroid
    
    joined = gpd.sjoin(hex_centroids, poly_gdf[['name', 'geometry']], how='inner', predicate='intersects')
    
    # Aggregate
    agg_df = joined.groupby('name').agg({
        'risk_da': 'mean',
        'risk_aw': 'mean',
        'divergence': 'mean',
        'norm_exposure_da': 'sum',
        'hazard_score': 'mean',
        'ndvi_stress': 'mean',
        'rainfall_deficit': 'mean',
        'dist_water_km': 'mean',
        'dist_barrier_km': 'mean',
        'mitigation_score': 'mean',
        'land_tenure': lambda x: x.mode()[0] if not x.mode().empty else 'other_community_land'
    }).reset_index()
    
    # Drop columns from poly_gdf that we are aggregating from hexes to avoid _x / _y suffixes
    cols_to_drop = [c for c in agg_df.columns if c in poly_gdf.columns and c != 'name']
    poly_gdf_clean = poly_gdf.drop(columns=cols_to_drop)
    
    poly_scored = poly_gdf_clean.merge(agg_df, on='name', how='left')
    poly_scored['risk_score'] = (poly_scored['risk_da'] * 100).fillna(0).round(1)
    
    # Ensure risk_da has no NaNs for the cut
    risk_vals = poly_scored['risk_da'].fillna(0.0)
    poly_scored['risk_level'] = pd.cut(risk_vals, bins=[-0.1, 0.33, 0.66, 1.1], labels=['LOW', 'MEDIUM', 'HIGH'])
    
    # Re-create columns that app.py expects from the old RiskEngine
    if 'dist_water_km' in poly_scored.columns:
        poly_scored['water_proximity'] = np.clip(1.0 - (poly_scored['dist_water_km'] / 15.0), 0.0, 1.0).round(2)
    else:
        poly_scored['water_proximity'] = 0.5
        
    if 'dist_park_km' in poly_scored.columns:
        poly_scored['boundary_proximity'] = np.clip(1.0 - (poly_scored['dist_park_km'] / 30.0), 0.0, 1.0).round(2)
    else:
        poly_scored['boundary_proximity'] = 0.5
        
    # Use our new dynamic Da exposure for the 'livestock_density' UI bar chart
    if 'norm_exposure_da' in poly_scored.columns:
        mx = poly_scored['norm_exposure_da'].max()
        if mx > 0:
            poly_scored['livestock_density'] = (poly_scored['norm_exposure_da'] / mx).round(2)
        else:
            poly_scored['livestock_density'] = 0.0
    else:
        poly_scored['livestock_density'] = 0.5
        
    if 'corridor_obstruction' not in poly_scored.columns:
        poly_scored['corridor_obstruction'] = 0.5
    
    # Dynamically generate primary drivers
    def get_drivers(row):
        drivers = []
        if row.get('ndvi_stress', 0) > 0.6: drivers.append('High Vegetation Stress')
        if row.get('water_proximity', 0) > 0.6: drivers.append('Water Scarcity')
        if row.get('boundary_proximity', 0) > 0.6: drivers.append('Proximity to National Park Boundary')
        if row.get('livestock_density', 0) > 0.6: drivers.append('Livestock Grazing Density')
        if row.get('corridor_obstruction', 0) > 0.6: drivers.append('Corridor Obstruction')
        
        if not drivers:
            drivers.append('Exposure (Da) x Hazard') # Default fallback
            
        return ', '.join(drivers)
        
    poly_scored['primary_drivers'] = poly_scored.apply(get_drivers, axis=1)
    

        
    # Dummy SMS advisory to prevent KeyError
    poly_scored['sms_advisory'] = "ALERT: " + poly_scored['risk_level'].astype(str) + " risk status computed via Dasymetric Exposure model."
    
    return poly_scored
