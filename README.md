# 🛡️ BOMA-SHIELD — Early Warning & Spatial Conflict Risk Assessment

> **Human-Wildlife Conflict Risk Assessment & Spatial Early Warning System for the Amboseli-Tsavo-Kilimanjaro Ecosystem.**

---

## 📌 Executive Summary

Drought pushes wildlife out of core conservation areas and into neighbouring farms and settlements in search of water and forage. Around ecosystems like Amboseli, this triggers a dual crisis: destroyed crops, killed livestock, and — in response — retaliatory killings of the very wildlife conservancies exist to protect. 

Current early-warning tools treat drought monitoring and wildlife conflict as separate problems, so no system tells a household or a ranger team where and when an incursion is likely before it happens.

**Boma Shield closes that gap.** It generates a weekly, zone-level incursion-risk score for the grazing corridors and settlements bordering a conservancy, combining satellite-derived drought signals with how close farms sit to the park boundary and water points, and with historical conflict incident records. Instead of a general seasonal warning, Boma Shield tells a ranger team *"Zone 3 is high-risk this week"* and tells households in that corridor to reinforce their boma or move livestock — giving them days of lead time to act rather than reacting after an incursion.

## Core Architecture
Boma Shield leverages a high-performance in-memory spatial database (DuckDB) and Generative AI (Google Gemini 2.5 Flash) to translate raw ecological variables into predictive threat maps.

> **Architectural Note on Group Ranches**: Group ranch boundaries represent land tenure and community management areas, not physical barriers — the Amboseli ecosystem is functionally unfenced and wildlife/livestock movement is continuous across these boundaries and into Amboseli National Park. Ranch boundaries are used for reporting and (where data exists) mitigation-program attribution, not as a hazard or exclusion factor.

Primary users are agropastoral households living along conservancy boundaries and the ranger teams who patrol them.

---

## 🌟 Key Features

- **🗺️ Interactive Risk Choropleth Map**: Real-time Folium & Streamlit portal mapping multi-criteria risk scores (LOW, MEDIUM, HIGH) across all 28 conservancies.
- **🛰️ Live Google Earth Engine (GEE) Integration**:
  - **Sentinel-2 10m Surface Reflectance NDVI**: Cloud-masked 10m resolution vegetation stress monitoring.
  - **CHIRPS Daily Rainfall**: 10-day dekad precipitation deficits.
- **📍 Multi-Layer Spatial Overlays**:
  - **1,770 KML Water Points**: Waterhole proximity mapping.
  - **4 Surrounding National Parks**: Protected area edge boundary proximity (Amboseli, Tsavo West, Kilimanjaro, Chyulu Hills).
  - **826 Human Towns & Settlements**: Human encroachment and settlement density (`busytown.geojson`).
  - **Georeferenced HWC Incident Base Rates**: Historical incident markers for validation.
- **📉 4-Week Risk Trajectory Analysis**: Historical 4-week dekad time-series tracking vegetation degradation and drought evolution.
- **⚖️ Dynamic Weight Sliders**: Transparent weight adjustment based on conservation literature (Mukeka et al.).
- **📲 Africa's Talking SMS Dispatch**: Live SMS advisory alerts sent to rangers, pastoralist community leaders, and conservancy managers.

---

## 📐 Multi-Criteria Risk Formula

$$\text{Risk Score} = S \times \sum_{i=1}^{6} (w_i \cdot x_i)$$

Where:
- $x_1$ = Vegetation Stress (Sentinel-2 10m NDVI)
- $x_2$ = Rainfall Deficit (CHIRPS 10-day dekad)
- $x_3$ = Waterhole Proximity Score
- $x_4$ = Park Boundary Edge Proximity Score
- $x_5$ = Livestock & Pastoralist Density Proxy
- $x_6$ = Wildlife Corridor Obstruction Score
- $S$ = Seasonal Peak Multiplier (e.g. Late Dry Season = 1.25x)

---

## 🚀 Quick Start

### 1. Prerequisites & Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/charity-gis/BOMA-SHIELD.git
cd BOMA-SHIELD
pip install -r requirements.txt
```

### 2. Google Earth Engine (GEE) Authorization

Authenticate your Google Cloud Project ID for live Sentinel-2 satellite queries:

```bash
python authenticate_gee.py YOUR_PROJECT_ID
```

### 3. Launch Boma Shield Dashboard

```bash
streamlit run app.py
```
Open **`http://localhost:8501`** in your browser.

---

## 📁 Project Structure

```text
BOMA-SHIELD/
├── app.py                      # Main Streamlit + Folium Web Portal
├── authenticate_gee.py         # Google Earth Engine OAuth & Setup script
├── requirements.txt            # Python dependencies
├── .gitignore                  # Git ignore rules (Excludes GIS datasets & rasters)
└── src/
    ├── spatial_engine.py       # Spatial analysis & GeoPandas metric extraction
    ├── risk_engine.py          # Multi-criteria scoring & driver diagnostics
    ├── gee_fetcher.py          # Google Earth Engine live satellite downloader
    ├── fetch_real_data.py      # CHIRPS dekad raster sampling
    ├── sms_notifier.py         # Africa's Talking SMS API integration
    └── validation_data.py      # Historical HWC incident base rates
```

---

## 📄 License & Attribution

- Built for community conservancies, wildlife rangers, and pastoralist livelihoods in the Amboseli-Tsavo-Kilimanjaro landscape.
- Literature weights based on Mukeka et al. Human-Wildlife Conflict Studies.
