# Boma Shield — Official Hackathon Submission

## Inspiration
The Amboseli ecosystem is a breathtaking landscape where wildlife and pastoralist communities have coexisted for generations. However, severe droughts increasingly force wildlife like elephants out of core conservation areas and into neighboring farms seeking water. This Human-Wildlife Conflict leads to destroyed crops and tragic retaliatory killings of protected animals. Recently, this urgency was tragically underscored in Amboseli, where fifteen elephants died in July 2026. Investigations detected toxic substances within their carcasses, suspected as deliberate poisoning deeply linked to desperate resource competition. Current systems treat drought and wildlife conflict as separate, reactive problems, lacking the ability to warn vulnerable communities before an incursion occurs. Witnessing these irreversible tragedies highlighted a critical need for a bold, proactive solution. Boma Shield was born to shift conservation management from reactive incident reporting toward preemptive environmental vulnerability screening, thereby saving livelihoods and wildlife.

## Project Description & Problem Statement
As agricultural settlements expand into historic migration corridors, severe Human-Wildlife Conflict (HWC) has escalated across the Amboseli ecosystem. This endangers pastoralist livelihoods, human lives, and wildlife conservation. Current conservation tools are fundamentally reactive, logging incidents only after crops are destroyed or animals are killed. 

**Boma Shield** is a proactive Early Warning Risk Portal designed to mitigate HWC. It transforms conservation management by highlighting geographic zones most susceptible to conflict based on escalating environmental stressors. Intended for conservation rangers, local government authorities, and pastoralist leaders, the platform fuses real-time satellite Earth observation data with spatial modeling to identify susceptibility hotspots *before* incidents occur.

By calculating dynamic risk scores across Group Ranches and Conservancies, Boma Shield provides actionable intelligence. Conservation managers can preemptively deploy ranger units, secure vulnerable livestock kraals (*bomas*), and guide herds away from predator zones, fostering peaceful coexistence.

## What it does & Proposed Solution
Instead of attempting to predict exact wildlife movements, Boma Shield evaluates escalating environmental stressors and calculates a weekly risk score per geographic zone. 

When a zone's susceptibility threshold is breached, the platform automatically dispatches localized, bilingual (English and Swahili) SMS advisories to grassroots community leaders. For example, rather than a generic warning, it provides targeted intelligence: *"Zone 3, elevated risk this week — reinforce boma / move livestock to guarded corridor."* 

The platform also includes a Natural Language AI Assistant, allowing rangers and administrators to query the spatial database and analyze situational reports using plain English.

## Key Features & Innovation Highlights
- **Live Satellite Susceptibility Engine:** Ingests real-time 30-day vegetation stress (NDVI) and rainfall deficit (CHIRPS) satellite data via Google Earth Engine.
- **AI Natural Language Assistant:** Dynamically translates plain English questions into safe spatial DuckDB SQL queries rendered instantly on an interactive map.
- **Last-Mile Bilingual SMS Integration:** High-risk triggers automatically dispatch localized warnings to community leaders via the TalkSasa API.
- **Fast In-Memory Analytics:** Uses DuckDB's Spatial Extension to evaluate proximity to waterholes, park boundaries, and migration corridors.

## How we built it & Technologies Used
We executed our build over a rapid development sprint, layering high-performance tools to bridge complex data with last-mile communication:

- **The Core Engine (DuckDB):** We utilized DuckDB with its Spatial Extension for ultra-fast, in-memory geometric queries (`ST_Intersects`, `ST_Distance`).
- **Satellite Data (Google Earth Engine):** We built a pipeline to ingest real-time Sentinel-2 and CHIRPS data.
- **Generative AI (Groq & Gemini):** We integrated Llama-3.3-70B and Gemini 2.5 Flash to power our Text-to-Spatial-SQL engine.
- **Frontend (Streamlit & Folium):** Built a mobile-responsive, interactive choropleth map dashboard.
- **Communications:** Wired up a SQLite database to manage contacts and dispatch automated SMS alerts via the TalkSasa API.

**The Multi-Criteria Scoring Formula:** We designed a transparent, literature-informed risk score using the following equation:

$$ \text{Risk Score} = S \times \sum_{i=1}^{6} (w_i \cdot x_i) $$

Where \\( S \\) is a seasonal peak multiplier, and the variables \\( x_i \\) represent normalized stressors (Vegetation, Rainfall, Waterhole Proximity, Boundary Proximity, Livestock Density, Corridor Obstruction) adjusted by their respective weights \\( w_i \\).

## Challenges we ran into
1. **The Data Access Bottleneck:** We initially wanted to train a machine-learning classifier, but high-resolution historical incident data wasn't accessible within our timeframe. We pivoted to a transparent weighted multi-criteria risk score based on published literature (e.g., Mukeka et al.), completely removing the data dependency.
2. **Data Sparsity:** OpenStreetMap (OSM) fence tagging in our target region was thin. To keep corridor obstruction scoring accurate, we had to engineer a fallback: treating road and dense-settlement intersections as proxies for blocked migration corridors.
3. **Defensive Security:** To ensure a frictionless demo without password walls, we engineered application-layer SQL regex blocklists (blocking `READ_CSV`, etc.) and API rate-limiting to prevent DuckDB file-reading vulnerabilities.
4. **Model-Freeze Discipline:** We ruthlessly froze our scoring logic by the mid-point deadline to ensure we could finish the dashboard and SMS integration on time.

## Accomplishments that we're proud of
- **Last-Mile Impact:** We successfully bridged abstract, terabyte-scale satellite data with simple, life-saving SMS messages for pastoralist communities.
- **Text-to-Spatial-SQL:** Building an AI assistant that can accurately and safely translate questions like *"Show water points near settlements"* into spatial queries rendered on an interactive map.
- **Pragmatic Architecture:** Delivering an end-to-end spatial risk engine that doesn't rely on uninterpretable "black box" models, but uses transparent, literature-backed weights that conservationists can trust.

## What we learned
Building Boma Shield reinforced the value of **pragmatic engineering in conservation tech**. We learned that a deterministic, literature-backed formula ships faster and is often more transparent than complex machine learning when data is scarce. 

We also learned the harsh reality of "rough-but-shipped" vs. "perfect-but-late"—enforcing a model freeze saved our project timeline. Lastly, we proved that a dashboard is only half the battle; true impact requires pushing insights directly to the people on the ground in their native languages.

## What's next for BOMA-SHIELD
Our hackathon prototype is just the beginning. We plan to:
- **Incorporate New Variables:** Add tracking for invasive species spread and water infrastructure status.
- **Auto-Tuning Weights:** Transition our architecture to auto-tune its weights against validation samples as conservancies log more precise incident data over time.
- **Scale the Ecosystem:** Expand Boma Shield beyond the Amboseli-Tsavo-Kilimanjaro landscape to protect pastoralist communities and wildlife corridors across Sub-Saharan Africa.

---
## Links & Deliverables
- **Working Prototype:** [Boma-Shield Live App](https://your-custom-name.streamlit.app) *(Replace with your live link)*
- **Source Code Repository:** [GitHub Repository](https://github.com/yourusername/BOMASHIELD) *(Replace with your GitHub repo link)*
- **Demo Video:** [Boma-Shield Video Demo](https://youtu.be/your-video-link) *(Replace with your video link)*

---
## Compliance & Declarations
- **Original Work & Integrity:** This submission is entirely original work created exclusively by our team. It does not infringe upon any third-party intellectual property rights.
- **External Tools & Disclosures:** We proudly utilized open-source datasets, libraries, and APIs: DuckDB, GeoPandas, Streamlit, Folium, Google Earth Engine, Groq Cloud LLMs, and TalkSasa Bulk SMS API.
- **Intellectual Property Rights:** The team retains ownership of the code and ideas developed for Boma Shield while granting organizers permission to showcase the project for evaluation and reporting.
