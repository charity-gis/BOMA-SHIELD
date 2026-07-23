import streamlit as st
import pandas as pd
import numpy as np
import geopandas as gpd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
import json
import importlib

import src.spatial_engine
import src.risk_engine
import src.risk_score
import src.validation_data
import src.sms_notifier
from dotenv import load_dotenv
load_dotenv()
from src.ai_query import generate_sql, run_query
importlib.reload(src.spatial_engine)
importlib.reload(src.risk_engine)
importlib.reload(src.risk_score)
importlib.reload(src.validation_data)
importlib.reload(src.sms_notifier)

from src.spatial_engine import SpatialEngine
from src.risk_engine import RiskEngine
from src.validation_data import ValidationData
from src.sms_notifier import SMSNotifier


# Page Config was moved to app.py

# Custom Styling (Glassmorphism & Sleek Dark Theme)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    .stApp {
        background: linear-gradient(135deg, #022c22 0%, #064e3b 100%);
        color: #ecfdf5;
    }
    
    /* Metric Cards */
    .metric-card {
        background: rgba(6, 78, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(12px);
        border-radius: 16px;
        padding: 18px 24px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(16, 185, 129, 0.5);
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #34d399, #10b981);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Risk Badges */
    .badge-high {
        background-color: rgba(239, 68, 68, 0.2);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.4);
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
    }
    .badge-medium {
        background-color: rgba(245, 158, 11, 0.2);
        color: #fbbf24;
        border: 1px solid rgba(245, 158, 11, 0.4);
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
    }
    .badge-low {
        background-color: rgba(16, 185, 129, 0.2);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.4);
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background: rgba(2, 44, 34, 0.95);
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }

    .stButton > button {
        background: linear-gradient(90deg, #059669, #10b981);
        color: white;
        border: none;
        border-radius: 10px;
        font-weight: 600;
        padding: 10px 20px;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background: linear-gradient(90deg, #047857, #059669);
        box-shadow: 0 4px 15px rgba(16, 185, 129, 0.4);
    }
</style>
""", unsafe_allow_html=True)

# Data Caching Functions
@st.cache_data
def load_base_spatial(week_key="2024-W39"):
    spatial = SpatialEngine()
    df_zones = spatial.get_zone_spatial_features(selected_dekad=week_key)
    return df_zones, spatial.gdf_waterpoints, spatial.gdf_parks, spatial.gdf_settlements



@st.cache_data
def load_incidents():
    return ValidationData.get_validation_incidents()

gdf_incidents = load_incidents()

# Title and caption removed since they are handled by st.navigation in app.py

# Ecosystem Spatial Scope Selector
scope_choice = st.sidebar.radio(
    "🌍 Analysis Scope",
    ["Ecosystem-Wide (All)", "Group Ranches", "Conservancies", "Parks Only"],
    index=0
)

# Optional Specific Ranch Filter
specific_ranch = "All"
if scope_choice in ["Group Ranches", "Conservancies"]:
    available_ranches = ["All"] + sorted([n for n in st.session_state.get('df_scored_all', pd.DataFrame({'name':[]}))['name'].unique() if pd.notnull(n)])
    if len(available_ranches) > 1:
        specific_ranch = st.sidebar.selectbox("Filter by Specific Ranch", available_ranches)

# Weekly Time-Series Selector
dekad_options = {
    "2024-W36": "📅 Week 1 (Aug 21-31)",
    "2024-W37": "📅 Week 2 (Sep 01-10)",
    "2024-W38": "📅 Week 3 (Sep 11-20)",
    "2024-W39": "📅 Week 4 (Sep 21-30) — Current"
}

selected_week_key = st.sidebar.selectbox(
    "📆 Satellite Monitoring Week",
    options=list(dekad_options.keys()),
    format_func=lambda k: dekad_options[k],
    index=3,
    help="Select weekly dekad to view satellite vegetation and rainfall risk evolution."
)

# Season Selector
season_choice = st.sidebar.selectbox(
    "🌧️ Seasonality Multiplier",
    options=list(RiskEngine.SEASON_MULTIPLIERS.keys()),
    index=0,
    help="Adjusts risk baseline based on historical seasonal conflict peaks."
)

with st.sidebar.expander("⚙️ Advanced Weight Configuration"):
    st.caption("Adjust transparent multi-criteria weights")
    w_ndvi = st.slider("Vegetation Stress (NDVI)", 0.0, 0.5, 0.25, 0.05)
    w_rain = st.slider("Rainfall Deficit (CHIRPS)", 0.0, 0.5, 0.20, 0.05)
    w_water = st.slider("Waterhole Proximity", 0.0, 0.5, 0.15, 0.05)
    w_bound = st.slider("Park Edge Boundary Proximity", 0.0, 0.5, 0.15, 0.05)
    w_dense = st.slider("Livestock/Grazing Density", 0.0, 0.5, 0.15, 0.05)
    w_corridor = st.slider("Corridor Obstruction Score", 0.0, 0.5, 0.10, 0.05)

custom_weights = {
    'ndvi_stress': w_ndvi,
    'rainfall_deficit': w_rain,
    'water_proximity': w_water,
    'boundary_proximity': w_bound,
    'livestock_density': w_dense,
    'corridor_obstruction': w_corridor
}

# Run Risk Scoring Engine for Selected Week
def get_scored_data_for_week(week_key, weights_dict, season_str):
    df_sp, gdf_wp, gdf_p, gdf_s = load_base_spatial(week_key=week_key)
    
    # Map season string to float [0, 1]
    season_val = 0.5
    if "Dry" in season_str: season_val = 0.0
    elif "Wet" in season_str: season_val = 1.0
    
    try:
        hex_gdf = gpd.read_parquet("data/parquet/hex_grid.parquet")
    except:
        # Fallback to df_sp if hex_grid isn't ready
        hex_gdf = df_sp.copy()
        hex_gdf['tlu_aw'] = hex_gdf.get('density_proxy', 0.1) * 1000
    
    import src.risk_score as rs
    hex_scored, corr = rs.run_pipeline(hex_gdf, weights_dict, season=season_val)
    st.session_state['da_aw_correlation'] = corr
    st.session_state['hex_scored'] = hex_scored
    
    poly_scored = rs.rollup_to_polygons(hex_scored, df_sp)
    
    return poly_scored, gdf_wp, gdf_p, gdf_s

df_scored_all, gdf_waterpoints, gdf_parks, gdf_settlements = get_scored_data_for_week(selected_week_key, custom_weights, season_choice)

# Store global data in session state for other pages
st.session_state['df_scored_all'] = df_scored_all
st.session_state['gdf_waterpoints'] = gdf_waterpoints
st.session_state['gdf_parks'] = gdf_parks

# Filter by Spatial Scope Choice
if "Group Ranches" in scope_choice:
    df_scored = df_scored_all[df_scored_all['category'] == 'Group Ranch'].reset_index(drop=True)
elif "Conservancies" in scope_choice:
    df_scored = df_scored_all[df_scored_all['category'] == 'Conservancy'].reset_index(drop=True)
elif "Parks Only" in scope_choice:
    df_scored = df_scored_all[df_scored_all['category'] == 'National Park'].reset_index(drop=True)
else:
    df_scored = df_scored_all.reset_index(drop=True)

if specific_ranch != "All":
    df_scored = df_scored[df_scored['name'] == specific_ranch].reset_index(drop=True)

st.session_state['df_scored'] = df_scored

gdf_incidents = load_incidents()

# Compute Aggregated KPI Metrics
total_zones = len(df_scored)
high_risk_count = len(df_scored[df_scored['risk_level'] == 'HIGH'])
med_risk_count = len(df_scored[df_scored['risk_level'] == 'MEDIUM'])
avg_risk_score = round(df_scored['risk_score'].mean(), 1)
total_waterpoints = len(gdf_waterpoints)

# Header Section
st.title("🛡️ Boma Shield — Early Warning Risk Portal")
st.markdown(f"Dynamic weekly risk assessment and early warning system for the **Amboseli-Tsavo-Kilimanjaro Ecosystem**. Active Scope: **{scope_choice}** | **{dekad_options[selected_week_key]}**.")

# Top Metrics Banner
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Ecosystem Zones</div>
        <div class="metric-value">{total_zones}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">High Risk Zones</div>
        <div class="metric-value" style="background: linear-gradient(90deg, #ef4444, #f87171); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">{high_risk_count}</div>
    </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Moderate Risk</div>
        <div class="metric-value" style="background: linear-gradient(90deg, #f59e0b, #fbbf24); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">{med_risk_count}</div>
    </div>
    """, unsafe_allow_html=True)
with col4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Avg Risk Score</div>
        <div class="metric-value">{avg_risk_score}%</div>
    </div>
    """, unsafe_allow_html=True)
with col5:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Water Points</div>
        <div class="metric-value" style="background: linear-gradient(90deg, #38bdf8, #60a5fa); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">{total_waterpoints}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

st.subheader("🗺️ Amboseli Ecosystem Risk Map")

# Layer Toggles
l1, l2, l3, l4 = st.columns(4)
with l1:
    show_parks = st.checkbox("National Parks", value=True)
with l2:
    show_waterpoints = st.checkbox("Water Points", value=True)
with l3:
    show_settlements = st.checkbox("Towns/Settlements", value=False)
with l4:
    show_incidents = st.checkbox("Incident Sample", value=True)

map_style = st.selectbox("Map Style", ["CartoDB dark_matter", "OpenStreetMap", "CartoDB positron"], index=0)

# Initialize Folium Map centered around Amboseli (-2.7, 37.35)
m = folium.Map(location=[-2.70, 37.35], zoom_start=9, tiles=map_style)


# Overlay National Parks (Dark Green Boundaries)
if show_parks and not gdf_parks.empty:
    folium.GeoJson(
        json.loads(gdf_parks.to_json()),
        style_function=lambda feature: {
            'fillColor': '#059669',
            'color': '#10b981',
            'weight': 2.5,
            'fillOpacity': 0.35,
            'dashArray': '4, 4'
        },
        tooltip=folium.GeoJsonTooltip(
            fields=['clean_name'],
            aliases=['National Park:'],
            localize=True
        )
    ).add_to(m)

# Risk Color Helper
def get_color(level):
    if level == 'HIGH':
        return '#ef4444'
    elif level == 'MEDIUM':
        return '#f59e0b'
    else:
        return '#10b981'

# Add Conservancy Polygons with Risk Choropleth Styling
if not df_scored.empty:
    geojson_data = json.loads(df_scored.to_json())
    
    folium.GeoJson(
        geojson_data,
        style_function=lambda feature: {
            'fillColor': get_color(feature['properties']['risk_level']),
            'color': '#ffffff',
            'weight': 1.5,
            'fillOpacity': 0.55
        },
        highlight_function=lambda feature: {
            'weight': 3.5,
            'color': '#38bdf8',
            'fillOpacity': 0.75
        },
        tooltip=folium.GeoJsonTooltip(
            fields=['name', 'category', 'land_tenure', 'risk_level', 'risk_score', 'ndvi_stress', 'dist_water_km', 'dist_barrier_km'],
            aliases=['Zone', 'Category', 'Land Tenure', 'Risk Level', 'Risk Score (%)', 'NDVI Stress', 'Water Dist (km)', 'Park Dist (km)'],
            localize=True
        )
    ).add_to(m)

# Overlay Towns & Human Settlements
if show_settlements and not gdf_settlements.empty:
    settle_cluster = MarkerCluster(name="Towns & Settlements").add_to(m)
    # Sample max 150 settlements for fast rendering
    sample_busy = gdf_settlements.sample(n=min(150, len(gdf_settlements)), random_state=42)
    for _, s in sample_busy.iterrows():
        centroid = s.geometry.centroid
        s_name = s.get('name') or s.get('place') or "Settlement"
        folium.CircleMarker(
            location=[centroid.y, centroid.x],
            radius=4,
            color='#a855f7',
            fill=True,
            fill_color='#c084fc',
            fill_opacity=0.85,
            popup=f"Settlement: {s_name}"
        ).add_to(settle_cluster)

# Overlay Water Points
if show_waterpoints and not gdf_waterpoints.empty:
    wp_cluster = MarkerCluster(name="Water Points").add_to(m)
    for _, wp in gdf_waterpoints.iterrows():
        # Ensure we are using a point coordinate (some geometries might be LineStrings)
        geom = wp.geometry.centroid if not wp.geometry.geom_type == 'Point' else wp.geometry
        folium.CircleMarker(
            location=[geom.y, geom.x],
            radius=4,
            color='#3b82f6',
            fill=True,
            fill_color='#60a5fa',
            fill_opacity=0.8,
            popup=f"Water Point: {wp.get('name', 'Unknown')}"
        ).add_to(wp_cluster)

# Overlay Incident Base Rate Sample
if show_incidents:
    inc_cluster = MarkerCluster(name="Base Rate Incidents").add_to(m)
    for _, inc in gdf_incidents.iterrows():
        folium.Marker(
            location=[inc['lat'], inc['lon']],
            icon=folium.Icon(color="red" if "Lion" in inc['type'] or "Crop" in inc['type'] else "orange", icon="warning-sign"),
            popup=f"<b>{inc['type']}</b><br>Date: {inc['date']}<br>{inc['details']}"
        ).add_to(inc_cluster)

# Dynamic Legend HTML
legend_html = '''
<div style="background-color: rgba(6, 78, 59, 0.9); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.2); display: flex; flex-wrap: wrap; gap: 15px; margin-bottom: 10px; font-size: 0.9rem;">
    <div style="display:flex; align-items:center;"><div style="width:15px; height:15px; background-color:#ef4444; border-radius:3px; margin-right:5px;"></div> High Risk (>= 66%)</div>
    <div style="display:flex; align-items:center;"><div style="width:15px; height:15px; background-color:#f59e0b; border-radius:3px; margin-right:5px;"></div> Medium Risk (33-66%)</div>
    <div style="display:flex; align-items:center;"><div style="width:15px; height:15px; background-color:#10b981; border-radius:3px; margin-right:5px;"></div> Low Risk (< 33%)</div>
    <div style="display:flex; align-items:center;"><div style="width:10px; height:10px; background-color:#0284c7; border:2px solid #38bdf8; border-radius:50%; margin-right:5px;"></div> Water Point</div>
    <div style="display:flex; align-items:center;"><div style="width:10px; height:10px; background-color:#c084fc; border:2px solid #a855f7; border-radius:50%; margin-right:5px;"></div> Town/Settlement</div>
    <div style="display:flex; align-items:center;"><div style="width:20px; height:4px; border-top:2px dashed #10b981; margin-right:5px;"></div> National Park Boundary</div>
</div>
'''
st.markdown(legend_html, unsafe_allow_html=True)

# Render Map in Streamlit
map_data = st_folium(m, width="100%", height=600)

st.markdown("---")
st.subheader("📊 Zone Risk Inspection")

# Conservancy Selection dropdown
zone_names = df_scored['name'].tolist()
selected_zone_name = st.selectbox("Select Conservancy / Zone:", options=zone_names, index=min(7, len(zone_names)-1))

selected_zone = df_scored[df_scored['name'] == selected_zone_name].iloc[0]

lvl = selected_zone['risk_level']
score = selected_zone['risk_score']
badge_class = f"badge-{lvl.lower()}"

st.markdown(f"""
<div style="background: rgba(6, 78, 59, 0.7); padding: 16px; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.1);">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <h3 style="margin: 0; color: #f8fafc;">{selected_zone['name']}</h3>
        <span class="{badge_class}">{lvl} ({score}%)</span>
    </div>
    <p style="margin-top: 8px; color: #94a3b8; font-size: 0.9rem;">
        Area: <b>{selected_zone['area_km2']} km²</b> | Water Dist: <b>{selected_zone['dist_water_km']} km</b> | Park Dist: <b>{selected_zone['dist_park_km']} km</b>
    </p>
    <p style="color: #cbd5e1; font-size: 0.95rem; margin-bottom: 0;">
        <b>Primary Drivers:</b> {selected_zone['primary_drivers']}
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# 2-Column Layout for Zone Detail Charts
c1, c2 = st.columns(2)

with c1:
    st.write("##### 📈 Risk Driver Factors (0.0 to 1.0)")
    
    factor_df = pd.DataFrame({
        'Factor': [
            'Vegetation Stress (NDVI)',
            'Rainfall Deficit (CHIRPS)',
            'Waterhole Crowding',
            'Park Edge Proximity',
            'Livestock Grazing Density',
            'Corridor Obstruction'
        ],
        'Score': [
            selected_zone['ndvi_stress'],
            selected_zone['rainfall_deficit'],
            selected_zone['water_proximity'],
            selected_zone['boundary_proximity'],
            selected_zone['livestock_density'],
            selected_zone['corridor_obstruction']
        ]
    })
    
    st.bar_chart(factor_df.set_index('Factor'), color='#38bdf8', height=240)

with c2:
    # 4-Week Risk Trajectory Chart
    st.write("##### 📉 4-Week Weekly Risk Score Trajectory (%)")
    weekly_scores = []
    w_keys = list(dekad_options.keys())
    for w_key in w_keys:
        df_w, *_ = get_scored_data_for_week(w_key, custom_weights, season_choice)
        z_w = df_w[df_w['name'] == selected_zone_name]
        score_val = z_w['risk_score'].values[0] if not z_w.empty else selected_zone['risk_score']
        weekly_scores.append(score_val)
        
    trend_df = pd.DataFrame({
        'Week': ["Week 1", "Week 2", "Week 3", "Week 4 (Current)"],
        'Risk Score (%)': weekly_scores
    }).set_index('Week')
    
    st.line_chart(trend_df, color='#ef4444' if lvl == 'HIGH' else ('#f59e0b' if lvl == 'MEDIUM' else '#10b981'), height=240)

st.markdown("---")
st.caption("🛡️ **Boma Shield** — Transparent Multi-Criteria HWC Early Warning System | Developed for Amboseli Conservancies & Pastoralist Communities.")
