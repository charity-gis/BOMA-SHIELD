import streamlit as st

# Must be the very first Streamlit command
st.set_page_config(
    page_title="Boma Shield — HWC Risk Assessment",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Define pages
main_page = st.Page("app_main.py", title="Ecosystem Risk Map", default=True)
sms_page = st.Page("pages/1_SMS_Alerts.py", title="SMS Alerts")
ai_page = st.Page("pages/2_AI_Query.py", title="AI Query")

report_page = st.Page("pages/3_Report_Generator.py", title="Generate Report")

# Execute navigation
pages = {
    " Boma Shield — Early Warning Risk Portal": [main_page, sms_page, ai_page, report_page]
}
pg = st.navigation(pages)
pg.run()

