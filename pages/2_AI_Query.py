import streamlit as st
import pandas as pd
import json

# Page config moved to app.py

try:
    import importlib
    import src.ai_query
    importlib.reload(src.ai_query)
    from src.ai_query import generate_sql, run_query, generate_report_answer
    from src.ui_helpers import load_cti_theme

    # Apply CTI Theme
    load_cti_theme()
except ImportError:
    st.error("Could not import AI Query modules. Ensure google-genai is installed.")

st.title(" Natural Language Assistant")
st.markdown("Query the spatial database using natural language or ask questions about the latest generated report.")

# Mode selection
query_mode = st.radio("Select Query Mode:", ["Query Database (SQL)", "Analyze Latest Report"], horizontal=True)

st.markdown("---")

if query_mode == "Query Database (SQL)":
    # Check if data is available in session state
    if 'df_scored' not in st.session_state:
        st.warning(" Please initialize the dataset on the main Risk Map page first.")

    user_prompt = st.text_area("Ask a question about the data (e.g., 'Show water points within 5 km of parks'):", height=100)
    
    col1, col2 = st.columns(2)
    with col1:
        temperature = st.slider("Model Temperature", 0.0, 1.0, 0.2, 0.1)
    with col2:
        result_view = st.selectbox("Result view", options=["Table", "Map", "Markdown Report", "Both"]) 

    if st.button(" Run Database Query", type="primary"):
        if user_prompt.strip():
            with st.spinner("Generating and executing query..."):
                try:
                    sql = generate_sql(user_prompt, temperature=temperature)
                    st.code(sql, language="sql")
                    
                    df_scored = st.session_state.get('df_scored')
                    result = run_query(sql, df_scored=df_scored)
                    df = result.df()
                    
                    if result_view in ("Table", "Both"):
                        st.subheader("Query Results (Table)")
                        st.dataframe(df)
                    
                    if result_view in ("Markdown Report", "Both"):
                        st.subheader("Query Results (Report Ready)")
                        markdown_str = df.to_markdown(index=False)
                        report_ready_text = f"### AI Query Results\n**Prompt:** {user_prompt}\n\n**Data Table:**\n\n{markdown_str}"
                        st.text_area("Copy this text for your report:", value=report_ready_text, height=200)
                        
                    if result_view in ("Map", "Both"):
                        import folium
                        from streamlit_folium import st_folium
                        import geopandas as gpd
                        from shapely import wkt
                        
                        # If the AI selected the 'wkt' column, convert it to a GeoDataFrame
                        if "wkt" in df.columns:
                            df["geometry"] = df["wkt"].apply(lambda x: wkt.loads(x) if pd.notnull(x) else None)
                            
                        if "geometry" in df.columns:
                            st.subheader("Spatial Results")
                            m = folium.Map(location=[-2.7, 37.35], zoom_start=9)
                            
                            gdf = gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")
                            # Drop null geometries to avoid folium crashes
                            gdf = gdf.dropna(subset=["geometry"])
                            
                            if not gdf.empty:
                                geojson = gdf.to_json()
                                folium.GeoJson(geojson).add_to(m)
                                st_folium(m, width="100%", height=500)
                            else:
                                st.warning("No valid spatial features found in the result to display on the map.")
                        
                except Exception as e:
                    st.error(f"Query error: {e}")
        else:
            st.warning("Please enter a question.")

else:
    # Analyze Latest Report Mode
    if 'latest_report_text' not in st.session_state:
        st.warning(" No report found in memory. Please go to the **Report Generator** page and load it first to generate a report.")
    else:
        report_text = st.session_state['latest_report_text']
        
        with st.expander("View Currently Loaded Report"):
            st.text(report_text)
            
        user_prompt = st.text_area("Ask a question about this report (e.g., 'What are the main causes of stress?'):", height=100)
        temperature = st.slider("Model Temperature", 0.0, 1.0, 0.2, 0.1)
        
        if st.button(" Ask AI", type="primary"):
            if user_prompt.strip():
                with st.spinner("Analyzing report..."):
                    try:
                        answer = generate_report_answer(user_prompt, report_text, temperature=temperature)
                        st.subheader("AI Answer")
                        st.write(answer)
                    except Exception as e:
                        st.error(f"AI Analysis error: {e}")
            else:
                st.warning("Please enter a question.")
