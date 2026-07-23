# Boma Shield — Hackathon Submission

## Project Overview
Boma Shield is an Early Warning Risk Portal designed to mitigate Human-Wildlife Conflict (HWC) in the Amboseli ecosystem. As human settlements and agricultural zones expand into historic wildlife corridors, conflicts—such as livestock predation and crop destruction by elephants and predators—have escalated. This threatens both pastoralist livelihoods and long-term wildlife conservation efforts.

Boma Shield addresses this meaningful challenge by providing a proactive, predictive risk assessment platform. Intended for use by conservation rangers, local government authorities, and pastoralist community leaders, the platform analyzes ecological and spatial data to forecast conflict hotspots. Instead of reacting to incidents after they occur, stakeholders are empowered with targeted intelligence to preemptively deploy ranger patrols, secure specific kraals (bomas), and adjust livestock grazing routes away from high-risk perimeters. By bridging the gap between advanced spatial modeling and grassroots conservation, Boma Shield protects community assets and fosters peaceful coexistence with Kenya’s iconic wildlife. *(155 words)*

## Solution Details
Boma Shield leverages a highly innovative, multi-layered architecture to deliver real-time intelligence. At its core, the platform ingests complex spatial geodata (conservancies, park boundaries, water points, and settlements) using a high-performance in-memory database engine (DuckDB with spatial extensions).

The key innovation is the integration of predictive algorithms and Generative AI. The system dynamically calculates a "Risk Score" for every conservancy by mathematically evaluating primary conflict drivers—such as vegetation stress, water scarcity, grazing density, and proximity to national park boundaries. When a high-risk zone is identified, Boma Shield triggers a localized, bilingual (English and Swahili) SMS advisory payload dispatched directly to pastoralists and rangers via the TalkSasa Bulk SMS API, ensuring critical last-mile communication.

Furthermore, Boma Shield pioneers AI creativity through a Natural Language Database Query engine. Powered by Google's Gemini 2.5 Flash LLM, non-technical users can type plain English questions (e.g., "Show water points near settlements") which the AI dynamically translates into complex spatial SQL queries. These queries are executed securely on the backend, instantly rendering targeted geographic intelligence on an interactive map. *(179 words)*

## Prototype
- **Working Application:** [Insert Web App / Streamlit Cloud URL Here]
- **Demo Video (Max 5 mins):** [Insert YouTube/Drive Video URL Here]

## Technical Information
- **Frontend / UI:** Streamlit (Python), Folium (Interactive Mapping)
- **Backend / Database:** DuckDB (High-speed SQL with Spatial extension), GeoPandas, Shapely
- **AI & Emerging Tech:** Google GenAI SDK (Gemini 2.5 Flash) for intelligent Text-to-Spatial-SQL translation
- **Communications:** TalkSasa Bulk SMS API (Bilingual alert dispatch engine)
- **Data Engineering:** Automated Spatial Joins (ST_Intersects, ST_Distance), GeoJSON parsing
- **GitHub Repository:** [Insert Public GitHub Repo URL Here]

## Compliance & Declarations
In full adherence to the hackathon's official rules and guidelines, the Boma Shield team formally declares the following:
- **Original Work & Integrity:** This submission is entirely original work created exclusively by our team. It does not infringe upon any third-party intellectual property rights, and we have maintained strict integrity, ensuring no misleading information or copied solutions are included.
- **External Tools & Disclosures:** We proudly utilized the following open-source datasets, libraries, and external APIs (fully acknowledging their creators):
  - *Data & Libraries:* DuckDB, GeoPandas, Shapely, Streamlit, and Folium.
  - *Emerging Technologies:* Google Gemini 2.5 Flash API (AI capabilities).
  - *Digital Platforms:* TalkSasa Bulk SMS API (Communications platform).
- **Intellectual Property Rights:** The team retains ownership of the code and ideas developed for Boma Shield. We happily grant the organizers and sponsors permission to showcase our project for evaluation, reporting, and hackathon promotion purposes.
- **Code of Conduct:** Our team operated with the highest standard of professional collaboration, fostering a positive, respectful, and inclusive innovation environment throughout the hackathon.
