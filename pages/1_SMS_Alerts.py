import streamlit as st
import pandas as pd
from src.sms_notifier import SMSNotifier

# Page config moved to app.py

st.title("📱 Community SMS Early Warning Alert")
st.markdown("Dispatch targeted risk advisories to pastoralists and ranger teams.")

if 'df_scored' not in st.session_state:
    st.warning("⚠️ No risk data loaded! Please return to the main Risk Map to initialize the dataset.")
    st.stop()

df_scored = st.session_state['df_scored']

# Conservancy Selection dropdown
zone_names = df_scored['name'].tolist()
selected_zone_name = st.selectbox("Select Conservancy / Zone:", options=zone_names, index=min(7, len(zone_names)-1))

selected_zone = df_scored[df_scored['name'] == selected_zone_name].iloc[0]

lvl = selected_zone['risk_level']
score = selected_zone['risk_score']

st.markdown(f"### {selected_zone_name} - Risk Level: **{lvl}** ({score}%)")
st.markdown(f"**Primary Drivers:** {selected_zone['primary_drivers']}")

st.markdown("---")

advisory_text = selected_zone['sms_advisory']
st.text_area("Generated Plain-Language Advisory:", value=advisory_text, height=100)

phone_input = st.text_input("Recipient Phone Number (Pastoralist / Ranger Lead):", value="+254712345678")

if st.button("🚀 Dispatch SMS Alert via Africa's Talking", type="primary"):
    notifier = SMSNotifier()
    with st.spinner("Dispatching..."):
        result = notifier.send_alert(phone_input, advisory_text, selected_zone['name'])
        
        if result['status'] in ['SUCCESS', 'FALLBACK_SANDBOX']:
            st.success(f"✅ SMS Alert Dispatched to {phone_input}!")
            st.json(result)
        else:
            st.error(f"❌ Dispatch Error: {result.get('error')}")
