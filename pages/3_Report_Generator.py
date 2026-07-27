import streamlit as st
import pandas as pd
import json
from datetime import datetime
from src.ui_helpers import load_cti_theme

# Apply CTI Theme
load_cti_theme()

st.title(" Situation Report Generator")
st.markdown("Generate a comprehensive text report and risk map for specific areas or the entire ecosystem.")

if st.button("⬅️ Back to Ecosystem Risk Map", use_container_width=True):
    st.switch_page("app_main.py")
st.markdown("---")

if 'df_scored' not in st.session_state:
    st.warning(" No risk data loaded! Please return to the main Risk Map to initialize the dataset.")
    st.stop()

df_scored = st.session_state['df_scored']

# Settings for the report
col1, col2 = st.columns(2)
with col1:
    scope_options = ["Entire Ecosystem"] + sorted([n for n in df_scored['name'].unique() if pd.notnull(n)])
    selected_scope = st.selectbox("Select Report Scope:", scope_options)
with col2:
    period_of_analysis = st.text_input("Period of Analysis:", value=datetime.now().strftime("%B %Y") + " (Current Dekad)")

# Filter data based on scope
if selected_scope == "Entire Ecosystem":
    df_report = df_scored.copy()
    report_title = "Amboseli Ecosystem - Comprehensive Risk Report"
else:
    df_report = df_scored[df_scored['name'] == selected_scope].copy()
    report_title = f"{selected_scope} - Localized Risk Report"

# Calculate Metrics
total_zones = len(df_report)
high_risk_count = len(df_report[df_report['risk_level'] == 'HIGH'])
med_risk_count = len(df_report[df_report['risk_level'] == 'MEDIUM'])
avg_risk_score = round(df_report['risk_score'].mean(), 1) if total_zones > 0 else 0

# Determine most common stress drivers
if total_zones > 0:
    all_drivers = []
    for d in df_report['primary_drivers'].dropna():
        all_drivers.extend([x.strip() for x in d.split(",")])
    
    if all_drivers:
        driver_counts = pd.Series(all_drivers).value_counts()
        top_drivers = ", ".join([f"{k} ({v} zones)" if selected_scope == "Entire Ecosystem" else k for k, v in driver_counts.head(3).items()])
    else:
        top_drivers = "Baseline Conditions"
else:
    top_drivers = "N/A"

st.markdown("---")

# Generate the Text Report
report_text = f"""BOMA SHIELD SITUATION REPORT: {selected_scope.upper()}
======================================================
Period of Analysis: {period_of_analysis}
Date Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Summary Metrics
------------------------------------------------------
- Total Areas Assessed: {total_zones}
- High Risk Zones (Red): {high_risk_count}
- Moderate Risk Zones (Amber): {med_risk_count}
- Average Risk Score: {avg_risk_score}%

Primary Causes of Stress
------------------------------------------------------
The driving factors exacerbating human-wildlife conflict risk during this period are predominantly:
{top_drivers}

High-Risk Area Breakdown
------------------------------------------------------
"""

if high_risk_count > 0:
    for _, row in df_report[df_report['risk_level'] == 'HIGH'].iterrows():
        report_text += f"- {row['name']}: Risk Score {row['risk_score']}%. Drivers: {row['primary_drivers']}\n"
else:
    report_text += "- No high-risk areas detected in this scope.\n"

report_text += "\nRecommended Actions\n------------------------------------------------------\n"
if high_risk_count > 0 or med_risk_count > 0:
    report_text += "- Deploy Ranger Teams: Increase patrols in high-risk zones highlighted above.\n"
    report_text += "- Community Sensitization: Dispatch SMS alerts to pastoralists regarding dangerous water points.\n"
    report_text += "- Corridor Monitoring: Ensure identified obstruction points are cleared for wildlife movement.\n"
else:
    report_text += "- Continue baseline monitoring. No immediate critical interventions required.\n"

# Display Report
st.subheader(" Generated Report Text")
st.session_state['latest_report_text'] = report_text
st.text_area("You can copy this text directly into your documents:", value=report_text, height=400)

import geopandas as gpd
from shapely import wkt
import matplotlib.pyplot as plt
import contextily as cx
from fpdf import FPDF
import io
import os
import json
import folium
from streamlit_folium import st_folium

# Display Map
st.subheader(" Spatial Overview")

m = folium.Map(location=[-2.7, 37.35], zoom_start=9)

def get_color(risk):
    if risk == 'HIGH': return '#ef4444'
    if risk == 'MEDIUM': return '#f59e0b'
    return '#10b981'

if not df_report.empty:
    df_safe = df_report.copy()
    if 'geometry' in df_safe.columns:
        gdf_folium = gpd.GeoDataFrame(df_safe, geometry="geometry", crs="EPSG:4326")
        
        # Center map on scope
        bounds = gdf_folium.total_bounds
        if len(bounds) == 4:
            m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])
            
        geojson_data = json.loads(gdf_folium.to_json())
        
        folium.GeoJson(
            geojson_data,
            style_function=lambda feature: {
                'fillColor': get_color(feature['properties']['risk_level']),
                'color': '#ffffff',
                'weight': 1.5,
                'fillOpacity': 0.6
            },
            tooltip=folium.GeoJsonTooltip(
                fields=['name', 'risk_level', 'risk_score', 'primary_drivers'],
                aliases=['Zone', 'Risk Level', 'Score (%)', 'Drivers']
            )
        ).add_to(m)

        # Add static name labels to the Folium map
        for _, row in gdf_folium.iterrows():
            if row['geometry']:
                centroid = row['geometry'].centroid
                # Clean the name for display
                short_name = str(row['name']).replace(' Conservancy', '').replace(' National Park', '').replace(' Group Ranch', '').strip()
                folium.Marker(
                    location=[centroid.y, centroid.x],
                    icon=folium.DivIcon(
                        html=f'<div style="font-size: 9pt; font-weight: bold; color: black; text-shadow: 1px 1px 2px white; text-align: center; width: 100px; margin-left: -50px; margin-top: -10px;">{short_name}</div>'
                    )
                ).add_to(m)

# Add Legend
legend_html = '''
<div style="
    position: fixed; 
    bottom: 50px; left: 50px; width: 180px; height: 110px; 
    border:2px solid grey; z-index:9999; font-size:14px;
    background-color:white; opacity: 0.9; padding: 10px;
    border-radius: 5px; color: black;
    ">
    <b>Risk Levels</b><br>
    <i style="background:#ef4444;width:12px;height:12px;display:inline-block;border-radius:50%;margin-right:5px;"></i> High (&ge; 66%)<br>
    <i style="background:#f59e0b;width:12px;height:12px;display:inline-block;border-radius:50%;margin-right:5px;"></i> Medium (33-66%)<br>
    <i style="background:#10b981;width:12px;height:12px;display:inline-block;border-radius:50%;margin-right:5px;"></i> Low (&lt; 33%)
</div>
'''
m.get_root().html.add_child(folium.Element(legend_html))

st_folium(m, width="100%", height=500)

# ----------------------------------------
# PDF GENERATION
# ----------------------------------------
st.subheader(" Export to PDF")

def generate_pdf():
    # 1. Create static map image
    fig, ax = plt.subplots(figsize=(8, 6))
    has_map = False
    
    if df_report.empty:
        st.warning("Warning: The spatial dataframe is empty. The map cannot be generated.")
    elif 'geometry' not in df_report.columns:
        st.warning("Warning: The spatial dataframe is missing geometry data. The map cannot be generated.")
    else:
        try:
            gdf_local = gpd.GeoDataFrame(df_report, geometry="geometry", crs="EPSG:4326")
            gdf_web_mercator = gdf_local.to_crs(epsg=3857)
            
            # Define colors
            color_map = {'HIGH': '#ef4444', 'MEDIUM': '#f59e0b', 'LOW': '#10b981'}
            colors = gdf_web_mercator['risk_level'].map(color_map).fillna('#10b981')
            
            gdf_web_mercator.plot(ax=ax, color=colors, edgecolor='white', alpha=0.6, linewidth=1.5)
            
            # Add text labels to the PDF map
            for _, row in gdf_web_mercator.iterrows():
                if row['geometry']:
                    centroid = row['geometry'].centroid
                    short_name = str(row['name']).replace(' Conservancy', '').replace(' National Park', '').replace(' Group Ranch', '').strip()
                    ax.annotate(text=short_name, xy=(centroid.x, centroid.y), xytext=(0, 0), 
                                textcoords="offset points", fontsize=7, fontweight='bold', 
                                color='black', ha='center', va='center',
                                path_effects=[plt.matplotlib.patheffects.withStroke(linewidth=2, foreground='white')])
            
            try:
                cx.add_basemap(ax, source=cx.providers.CartoDB.Positron)
            except Exception as e:
                print("Basemap failed:", e)
                
            import matplotlib.patches as mpatches
            legend_patches = [
                mpatches.Patch(color='#ef4444', label='High Risk (>= 66%)', alpha=0.6),
                mpatches.Patch(color='#f59e0b', label='Medium Risk (33-66%)', alpha=0.6),
                mpatches.Patch(color='#10b981', label='Low Risk (< 33%)', alpha=0.6)
            ]
            ax.legend(handles=legend_patches, loc='lower right', title='Risk Levels', frameon=True, facecolor='white', framealpha=0.8)
                
            ax.set_axis_off()
            plt.title(f"{report_title} - Spatial Map")
            plt.tight_layout()
            has_map = True
        except Exception as e:
            st.error(f"Map Plotting Error: {str(e)}")
            print("Plotting error:", e)
            
    map_path = "temp_map.png"
    if has_map:
        plt.savefig(map_path, dpi=150, bbox_inches='tight')
    plt.close(fig)

    # 2. Generate PDF
    class PDF(FPDF):
        def header(self):
            self.set_font("helvetica", "B", 16)
            self.cell(0, 10, "BOMA SHIELD - SITUATION REPORT", border=False, align="C", new_x="LMARGIN", new_y="NEXT")
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font("helvetica", "I", 8)
            self.cell(0, 10, f"Page {self.page_no()}", align="C")

    pdf = PDF()
    pdf.add_page()
    
    # Title
    pdf.set_font("helvetica", "B", 14)
    pdf.cell(0, 10, report_title, new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("helvetica", "", 11)
    pdf.cell(0, 8, f"Period of Analysis: {period_of_analysis}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Date Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    # Summary Metrics
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 8, "Summary Metrics", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 11)
    pdf.cell(0, 8, f"  - Total Areas Assessed: {total_zones}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"  - High Risk Zones (Red): {high_risk_count}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"  - Moderate Risk Zones (Amber): {med_risk_count}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"  - Average Risk Score: {avg_risk_score}%", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    # Primary Causes
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 8, "Primary Causes of Stress", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 11)
    pdf.multi_cell(0, 8, f"The driving factors exacerbating human-wildlife conflict risk during this period are predominantly: {top_drivers}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    # Map
    if os.path.exists(map_path):
        pdf.image(map_path, w=170)
        os.remove(map_path)
    pdf.ln(5)
    
    # Breakdown
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 8, "High-Risk Area Breakdown", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 11)
    if high_risk_count > 0:
        for _, row in df_report[df_report['risk_level'] == 'HIGH'].iterrows():
            pdf.multi_cell(0, 8, f"  - {row['name']}: Risk Score {row['risk_score']}%. Drivers: {row['primary_drivers']}", new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.cell(0, 8, "  - No high-risk areas detected in this scope.", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    # Recommendations
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 8, "Recommended Actions", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 11)
    if high_risk_count > 0 or med_risk_count > 0:
        pdf.multi_cell(0, 8, "  - Deploy Ranger Teams: Increase patrols in high-risk zones highlighted above.", new_x="LMARGIN", new_y="NEXT")
        pdf.multi_cell(0, 8, "  - Community Sensitization: Dispatch SMS alerts to pastoralists regarding dangerous water points.", new_x="LMARGIN", new_y="NEXT")
        pdf.multi_cell(0, 8, "  - Corridor Monitoring: Ensure identified obstruction points are cleared for wildlife movement.", new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.multi_cell(0, 8, "  - Continue baseline monitoring. No immediate critical interventions required.", new_x="LMARGIN", new_y="NEXT")

    return pdf.output()

if st.button("Generate PDF Report", type="primary"):
    with st.spinner("Rendering map and compiling PDF..."):
        st.session_state['pdf_bytes'] = bytes(generate_pdf())
        
if 'pdf_bytes' in st.session_state:
    st.success("PDF generated successfully!")
    st.download_button(
        label=" Click Here to Download PDF",
        data=st.session_state['pdf_bytes'],
        file_name=f"{selected_scope.replace(' ', '_')}_Risk_Report.pdf",
        mime="application/pdf",
    )
