# 🛡️ Boma Shield — Early Warning & Risk Assessment System

> **Human-Wildlife Conflict Risk Assessment & Spatial Early Warning Portal for the Amboseli-Tsavo-Kilimanjaro Ecosystem.**

---

## 📌 Overview

**Boma Shield** is a spatial risk modeling and early warning portal designed to identify conditions under which **Human-Wildlife Conflict (HWC)**—such as elephant crop-raiding, lion livestock predation, and pastoralist boma raids—is most likely to occur.

Rather than predicting exact conflict events from historical incident logs alone, Boma Shield models the underlying ecological and spatial drivers across **28 community conservancies and ranches**, anchoring 4 major National Parks (**Amboseli**, **Tsavo West**, **Kilimanjaro**, and **Chyulu Hills**).

---

## 🌟 Key Features

- **🗺️ Interactive Risk Choropleth Map**: Real-time Folium & Streamlit portal mapping multi-criteria risk scores (LOW, MEDIUM, HIGH) across all 28 conservancies.
- **🛰️ Live Google Earth Engine (GEE) Integration**:
  - **Sentinel-2 10m Surface Reflectance NDVI**: Cloud-masked 10m resolution vegetation stress monitoring.
  - **CHIRPS Daily Rainfall**: 10-day dekad precipitation deficits.
- **📍 Multi-Layer Spatial Overlays**:
  - **1,770 KML Water Points**: Waterhole proximity mapping.
  - **4 Surrounding National Parks**: Protected area edge boundary proximity.
  - **826 Human Towns & Settlements**: Human encroachment and settlement density.
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
git clone https://github.com/YOUR_USERNAME/boma-shield.git
cd boma-shield
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
BOMASHIELD/
├── app.py                      # Main Streamlit + Folium Web Portal
├── authenticate_gee.py         # Google Earth Engine OAuth & Setup script
├── requirements.txt            # Python dependencies
├── .gitignore                  # Git ignore rules
├── AMBOSELI CONSERVANCIES.shp  # 28 Conservancy Polygons
├── national parks.shp          # 4 Surrounding National Parks
├── export (2).kml              # 1,770 Water Point Placemarks
├── busytown.geojson            # 826 Human Settlement Polygons
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
