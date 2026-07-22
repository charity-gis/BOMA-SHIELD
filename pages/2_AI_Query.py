import streamlit as st
import pandas as pd
import json

# Page config moved to app.py

try:
    from src.ai_query import generate_sql, run_query
except ImportError:
    st.error("Could not import AI Query modules. Ensure google-genai is installed.")

st.title("🤖 Natural Language Database Query")
st.markdown("Ask natural language questions about the Boma Shield database.")

# Check if data is available in session state
if 'df_scored' not in st.session_state:
    st.warning("⚠️ Please initialize the dataset on the main Risk Map page first.")

user_prompt = st.text_area("Ask a question about the data (e.g., 'Show water points within 5 km of parks'):", height=100)

col1, col2 = st.columns(2)
with col1:
    temperature = st.slider("Model Temperature", 0.0, 1.0, 0.2, 0.1)
with col2:
    result_view = st.selectbox("Result view", options=["Table", "Map", "Both"]) 

if st.button("🚀 Run Query", type="primary"):
    if user_prompt.strip():
        with st.spinner("Generating and executing query..."):
            try:
                sql = generate_sql(user_prompt, temperature=temperature)
                st.code(sql, language="sql")
                result = run_query(sql)
                df = result.df()
                
                if result_view in ("Table", "Both"):
                    st.subheader("Query Results (Table)")
                    st.dataframe(df)
                    
                if result_view in ("Map", "Both") and "geometry" in df.columns:
                    import folium
                    from streamlit_folium import st_folium
                    
                    st.subheader("Spatial Results")
                    m = folium.Map(location=[-2.7, 37.35], zoom_start=9)
                    geojson = df.dropna(subset=["geometry"]).to_json()
                    folium.GeoJson(geojson).add_to(m)
                    st_folium(m, width="100%", height=500)
                    
            except Exception as e:
                st.error(f"Query error: {e}")
    else:
        st.warning("Please enter a question.")
