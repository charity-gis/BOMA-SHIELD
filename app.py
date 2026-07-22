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
import src.validation_data
import src.sms_notifier
from dotenv import load_dotenv
load_dotenv()
from src.ai_query import generate_sql, run_query
importlib.reload(src.spatial_engine)
importlib.reload(src.risk_engine)
importlib.reload(src.validation_data)
importlib.reload(src.sms_notifier)

from src.spatial_engine import SpatialEngine
from src.risk_engine import RiskEngine
from src.validation_data import ValidationData
from src.sms_notifier import SMSNotifier


# Page Config
st.set_page_config(
    page_title="Boma Shield — HWC Risk Assessment & Early Warning System",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Glassmorphism & Sleek Dark Theme)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    .stApp {
        background: linear-gradient(135deg, #0b1120 0%, #151e32 100%);
        color: #f1f5f9;
    }
    
    /* Metric Cards */
    .metric-card {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(12px);
        border-radius: 16px;
        padding: 18px 24px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(59, 130, 246, 0.5);
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #38bdf8, #818cf8);
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
        background: rgba(15, 23, 42, 0.95);
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }

    .stButton > button {
        background: linear-gradient(90deg, #2563eb, #3b82f6);
        color: white;
        border: none;
        border-radius: 10px;
        font-weight: 600;
        padding: 10px 20px;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background: linear-gradient(90deg, #1d4ed8, #2563eb);
        box-shadow: 0 4px 15px rgba(37, 99, 235, 0.4);
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

# Sidebar Configuration
st.sidebar.title("🛡️ Boma Shield")
st.sidebar.caption("Human-Wildlife Conflict Risk Assessment & Early Warning System")
st.sidebar.markdown("---")

# Spatial Scope Selector
scope_choice = st.sidebar.selectbox(
    "🌐 Spatial Evaluation Scope",
    options=["Entire Amboseli Ecosystem Region (32 Zones)", "Conservancies & Group Ranches Only (28 Zones)", "National Parks Only (4 Parks)"],
    index=0,
    help="Switch between monitoring the entire ecosystem landscape or specific land designations."
)

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

# Factor Weights Fine-Tuning Sliders
st.sidebar.subheader("⚖️ Factor Weight Configuration")
st.sidebar.caption("Adjust transparent multi-criteria weights (Literature baseline: Mukeka et al.)")

w_ndvi = st.sidebar.slider("Vegetation Stress (NDVI)", 0.0, 0.5, 0.25, 0.05)
w_rain = st.sidebar.slider("Rainfall Deficit (CHIRPS)", 0.0, 0.5, 0.20, 0.05)
w_water = st.sidebar.slider("Waterhole Proximity", 0.0, 0.5, 0.15, 0.05)
w_bound = st.sidebar.slider("Park Edge Boundary Proximity", 0.0, 0.5, 0.15, 0.05)

# LLM Natural Language Query Interface
st.sidebar.subheader("🤖 Natural Language Query")
user_prompt = st.sidebar.text_area("Ask a question about the data (e.g., 'Show water points within 5 km of parks')", height=80)
temperature = st.sidebar.slider("Model Temperature", 0.0, 1.0, 0.2, 0.1)
result_view = st.sidebar.selectbox("Result view", options=["Table", "Map", "Both"]) 

if st.sidebar.button("Run Query"):
    if user_prompt.strip():
        try:
            sql = generate_sql(user_prompt, temperature=temperature)
            result = run_query(sql)
            df = result.df()
            if result_view in ("Table", "Both"):
                st.subheader("Query Results (Table)")
                st.dataframe(df)
            if result_view in ("Map", "Both") and "geometry" in df.columns:
                import folium
                from streamlit_folium import st_folium
                m = folium.Map(location=[-2.7, 37.35], zoom_start=9)
                geojson = df.dropna(subset=["geometry"]).to_json()
                folium.GeoJson(geojson).add_to(m)
                st_folium(m, width="100%", height=500)
        except Exception as e:
            st.error(f"Query error: {e}")
    else:
        st.warning("Please enter a question.")
w_dense = st.sidebar.slider("Livestock/Grazing Density", 0.0, 0.5, 0.15, 0.05)
w_corridor = st.sidebar.slider("Corridor Obstruction Score", 0.0, 0.5, 0.10, 0.05)

custom_weights = {
    'ndvi_stress': w_ndvi,
    'rainfall_deficit': w_rain,
    'water_proximity': w_water,
    'boundary_proximity': w_bound,
    'livestock_density': w_dense,
    'corridor_obstruction': w_corridor
}

# Run Risk Scoring Engine for Selected Week
def get_scored_data_for_week(week_key, weights_dict, season):
    df_sp, gdf_wp, gdf_p, gdf_s = load_base_spatial(week_key=week_key)
    risk_eng = RiskEngine(weights=weights_dict, season=season)
    return risk_eng.compute_risk(df_sp), gdf_wp, gdf_p, gdf_s

df_scored_all, gdf_waterpoints, gdf_parks, gdf_settlements = get_scored_data_for_week(selected_week_key, custom_weights, season_choice)

# Filter by Spatial Scope Choice
if "Conservancies" in scope_choice:
    df_scored = df_scored_all[df_scored_all['category'] != 'National Park'].reset_index(drop=True)
elif "Parks Only" in scope_choice:
    df_scored = df_scored_all[df_scored_all['category'] == 'National Park'].reset_index(drop=True)
else:
    df_scored = df_scored_all.reset_index(drop=True)

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

# Main 2-Column Dashboard Layout
left_col, right_col = st.columns([1.6, 1.0])

with left_col:
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
            fields=['name', 'risk_score', 'risk_level', 'primary_drivers'],
            aliases=['Conservancy:', 'Risk Score:', 'Level:', 'Primary Drivers:'],
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
        # Sample max 200 waterpoints for smooth rendering
        sample_wp = gdf_waterpoints.sample(n=min(200, len(gdf_waterpoints)), random_state=42)
        for _, wp in sample_wp.iterrows():
            folium.CircleMarker(
                location=[wp['lat'], wp['lon']],
                radius=3.5,
                color='#38bdf8',
                fill=True,
                fill_color='#0284c7',
                fill_opacity=0.8,
                popup=f"Water Point: {wp['name']}"
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


    # Render Map in Streamlit
    map_data = st_folium(m, width="100%", height=540)

with right_col:
    st.subheader("📊 Zone Risk Inspection")
    
    # Conservancy Selection dropdown
    zone_names = df_scored['name'].tolist()
    selected_zone_name = st.selectbox("Select Conservancy / Zone:", options=zone_names, index=min(7, len(zone_names)-1))
    
    selected_zone = df_scored[df_scored['name'] == selected_zone_name].iloc[0]
    
    lvl = selected_zone['risk_level']
    score = selected_zone['risk_score']
    badge_class = f"badge-{lvl.lower()}"
    
    st.markdown(f"""
    <div style="background: rgba(30, 41, 59, 0.7); padding: 16px; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.1);">
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
    
    # Breakdown of 6 Input Factors
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
    
    st.bar_chart(factor_df.set_index('Factor'), color='#38bdf8', height=200)

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
    
    st.line_chart(trend_df, color='#ef4444' if lvl == 'HIGH' else ('#f59e0b' if lvl == 'MEDIUM' else '#10b981'), height=180)

    st.markdown("---")

    
    # Early Warning SMS Dispatcher
    st.subheader("📱 Community SMS Early Warning Alert")
    
    advisory_text = selected_zone['sms_advisory']
    st.text_area("Generated Plain-Language Advisory:", value=advisory_text, height=100)
    
    phone_input = st.text_input("Recipient Phone Number (Pastoralist / Ranger Lead):", value="+254712345678")
    
    if st.button("🚀 Dispatch SMS Alert via Africa's Talking"):
        notifier = SMSNotifier()
        result = notifier.send_alert(phone_input, advisory_text, selected_zone['name'])
        
        if result['status'] in ['SUCCESS', 'FALLBACK_SANDBOX']:
            st.success(f"✅ SMS Alert Dispatched to {phone_input}!")
            st.json(result)
        else:
            st.error(f"❌ Dispatch Error: {result.get('error')}")

st.markdown("---")
st.caption("🛡️ **Boma Shield** — Transparent Multi-Criteria HWC Early Warning System | Developed for Amboseli Conservancies & Pastoralist Communities.")
