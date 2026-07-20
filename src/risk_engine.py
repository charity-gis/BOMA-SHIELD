import numpy as np
import pandas as pd

class RiskEngine:
    DEFAULT_WEIGHTS = {
        'ndvi_stress': 0.25,
        'rainfall_deficit': 0.20,
        'water_proximity': 0.15,
        'boundary_proximity': 0.15,
        'livestock_density': 0.15,
        'corridor_obstruction': 0.10
    }

    SEASON_MULTIPLIERS = {
        'Late Dry Season (Aug-Oct)': 1.25,
        'Early Dry Season (Jan-Mar)': 1.10,
        'Long Rains (Apr-Jun)': 0.80,
        'Short Rains (Nov-Dec)': 0.90
    }

    ACTION_TEMPLATES = {
        'HIGH': [
            "CRITICAL WARNING: High Human-Wildlife Conflict risk flagged for {zone_name}. Primary drivers: {drivers}. Recommended Action: Reinforce predator-proof bomas immediately, restrict night grazing along boundary, and deploy ranger mobile patrol unit to active corridor.",
            "ALERT: Elevated HWC risk in {zone_name} due to {drivers}. Pastoralists advised to group livestock into guarded night enclosures and avoid lone herding near waterpoints.",
            "HIGH RISK ADVISORY ({zone_name}): {drivers} elevating conflict probability. Action: Conservancies should dispatch night deterrent teams (flashlights/vuvuzelas) and alert wildlife response unit."
        ],
        'MEDIUM': [
            "MODERATE RISK NOTICE: {zone_name} showing moderate vulnerability driven by {drivers}. Action: Check boma fencing integrity and monitor waterhole access schedules.",
            "ADVISORY: Moderate conflict risk in {zone_name}. Key factors: {drivers}. Herders recommended to return livestock before 18:30 hrs."
        ],
        'LOW': [
            "NORMAL STATUS: Low conflict risk reported for {zone_name}. Environmental and corridor indicators stable. Routine monitoring active."
        ]
    }

    def __init__(self, weights=None, season='Late Dry Season (Aug-Oct)'):
        self.weights = weights if weights is not None else self.DEFAULT_WEIGHTS.copy()
        self.season = season
        self.normalize_weights()

    def normalize_weights(self):
        total = sum(self.weights.values())
        if total > 0:
            for k in self.weights:
                self.weights[k] /= total

    def compute_risk(self, df_zones, season=None):
        if season is not None:
            self.season = season

        season_mult = self.SEASON_MULTIPLIERS.get(self.season, 1.0)
        df = df_zones.copy()

        # Generate realistic/reproducible dynamic environmental indicators if missing
        np.random.seed(42)
        if 'ndvi_stress' not in df.columns:
            df['ndvi_stress'] = np.random.beta(a=2, b=3, size=len(df)).round(2)
        if 'rainfall_deficit' not in df.columns:
            df['rainfall_deficit'] = np.random.beta(a=2.5, b=2.5, size=len(df)).round(2)

        # Normalize distance features to 0-1 scores (closer = higher risk score)
        # Water proximity score (max dist ~15km)
        if 'dist_water_km' in df.columns:
            df['water_proximity'] = np.clip(1.0 - (df['dist_water_km'] / 15.0), 0.0, 1.0).round(2)
        else:
            df['water_proximity'] = 0.5

        # Boundary proximity score (max dist ~30km)
        if 'dist_park_km' in df.columns:
            df['boundary_proximity'] = np.clip(1.0 - (df['dist_park_km'] / 30.0), 0.0, 1.0).round(2)
        else:
            df['boundary_proximity'] = 0.5

        if 'density_proxy' in df.columns:
            df['livestock_density'] = df['density_proxy']
        else:
            df['livestock_density'] = 0.5

        if 'corridor_obstruction' not in df.columns:
            df['corridor_obstruction'] = 0.5

        # Compute Raw & Weighted Scores
        weighted_sum = (
            df['ndvi_stress'] * self.weights['ndvi_stress'] +
            df['rainfall_deficit'] * self.weights['rainfall_deficit'] +
            df['water_proximity'] * self.weights['water_proximity'] +
            df['boundary_proximity'] * self.weights['boundary_proximity'] +
            df['livestock_density'] * self.weights['livestock_density'] +
            df['corridor_obstruction'] * self.weights['corridor_obstruction']
        )

        # Apply seasonal multiplier and scale to 0 - 100
        raw_risk_pct = (weighted_sum * season_mult * 100.0).round(1)
        df['risk_score'] = np.clip(raw_risk_pct, 0.0, 100.0)

        # Assign risk labels
        conditions = [
            df['risk_score'] >= 70.0,
            (df['risk_score'] >= 40.0) & (df['risk_score'] < 70.0),
            df['risk_score'] < 40.0
        ]
        choices = ['HIGH', 'MEDIUM', 'LOW']
        df['risk_level'] = np.select(conditions, choices, default='LOW')

        # Identify dominant drivers & generate SMS advisory
        primary_drivers = []
        advisories = []
        
        factor_names = {
            'ndvi_stress': 'Vegetation Stress (NDVI)',
            'rainfall_deficit': 'Rainfall Deficit (CHIRPS)',
            'water_proximity': 'Waterhole Crowding',
            'boundary_proximity': 'Park Edge Proximity',
            'livestock_density': 'Livestock Grazing Density',
            'corridor_obstruction': 'Corridor Encroachment'
        }

        for idx, row in df.iterrows():
            row_factors = {
                k: row[k] * self.weights[k] for k in self.weights.keys()
            }
            # Top 2 factors
            sorted_factors = sorted(row_factors.items(), key=lambda x: x[1], reverse=True)[:2]
            top_driver_names = [factor_names[k] for k, _ in sorted_factors]
            driver_str = " & ".join(top_driver_names)
            primary_drivers.append(driver_str)

            # SMS recommendation selection
            lvl = row['risk_level']
            templates = self.ACTION_TEMPLATES[lvl]
            template = templates[idx % len(templates)]
            advisory = template.format(zone_name=row['name'], drivers=driver_str)
            advisories.append(advisory)

        df['primary_drivers'] = primary_drivers
        df['sms_advisory'] = advisories

        return df

if __name__ == "__main__":
    from src.spatial_engine import SpatialEngine
    spatial = SpatialEngine()
    df_spatial = spatial.get_zone_spatial_features()
    
    risk_engine = RiskEngine()
    df_scored = risk_engine.compute_risk(df_spatial)
    print(f"Risk engine calculated scores for {len(df_scored)} zones.")
    print(df_scored[['name', 'risk_score', 'risk_level', 'primary_drivers']].head(10))
