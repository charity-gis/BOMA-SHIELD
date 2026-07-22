import pytest
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Point

import src.risk_score as rs

@pytest.fixture
def dummy_hex_gdf():
    df = pd.DataFrame({
        'hex_id': ['h1', 'h2', 'h3'],
        'tlu_aw': [100.0, 50.0, 0.0],
        'ndvi_stress': [0.2, 0.8, 0.5],
        'rainfall_deficit': [0.1, 0.9, 0.4],
        'dist_water_km': [1.0, 10.0, 5.0],
        'dist_barrier_km': [0.5, 20.0, 10.0],
        'dist_settlement_km': [2.0, 15.0, 8.0],
        'dist_park_km': [0.1, 5.0, 2.5],
        'zone_name': ['ZoneA', 'ZoneA', 'ZoneB']
    })
    gdf = gpd.GeoDataFrame(df, geometry=[Point(0,0), Point(1,1), Point(2,2)], crs="EPSG:4326")
    return gdf

def test_exposure_covariates(dummy_hex_gdf):
    """Test that exposure correctly normalizes and applies weights."""
    res = rs.compute_exposure(dummy_hex_gdf.copy(), season=0.5)
    assert 'exposure_da' in res.columns
    assert 'exposure_aw' in res.columns
    # Da should shift more weight to h1 than h2 in ZoneA because h1 has lower stress/water dist
    assert res.loc[0, 'exposure_da'] > res.loc[1, 'exposure_da']
    
def test_hazard_covariates(dummy_hex_gdf):
    """Test that hazard ignores exposure covariates."""
    weights = {'boundary_proximity': 0.5, 'settlement_proximity': 0.5}
    res1 = rs.compute_hazard(dummy_hex_gdf.copy(), weights, season=0.5)
    
    # Change exposure covariates
    mod_gdf = dummy_hex_gdf.copy()
    mod_gdf['ndvi_stress'] = [0.9, 0.1, 0.2]
    mod_gdf['dist_water_km'] = [20.0, 0.1, 2.0]
    
    res2 = rs.compute_hazard(mod_gdf, weights, season=0.5)
    
    # Hazard should remain identical because it must explicitly exclude those!
    pd.testing.assert_series_equal(res1['hazard_score'], res2['hazard_score'])

def test_risk_computation(dummy_hex_gdf):
    """Test full pipeline yields non-null values."""
    weights = {'boundary_proximity': 0.5, 'settlement_proximity': 0.5}
    res, corr = rs.run_pipeline(dummy_hex_gdf.copy(), weights, season=0.5)
    
    assert res['risk_da'].notnull().all()
    assert res['risk_aw'].notnull().all()
    assert res['divergence'].notnull().all()
    assert isinstance(corr, float)
