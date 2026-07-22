import streamlit as st

# Must be the very first Streamlit command
st.set_page_config(
    page_title="Boma Shield — HWC Risk Assessment",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Define pages
main_page = st.Page("app_main.py", title="Ecosystem Risk Map", icon="🗺️", default=True)
sms_page = st.Page("pages/1_SMS_Alerts.py", title="SMS Alerts", icon="📱")
ai_page = st.Page("pages/2_AI_Query.py", title="AI Query", icon="🤖")

# Execute navigation
pg = st.navigation([main_page, sms_page, ai_page])
pg.run()
