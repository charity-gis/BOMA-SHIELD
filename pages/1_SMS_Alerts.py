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

# Language Selector
lang = st.radio("Select SMS Language:", ["Both (Bilingual)", "English Only", "Swahili (Kiswahili) Only"], horizontal=True)

st.markdown("---")

# Dictionary to map drivers to Swahili
swahili_drivers_map = {
    'High Vegetation Stress': 'Uhaba mkubwa wa malisho',
    'Water Scarcity': 'Uhaba wa maji',
    'Proximity to National Park Boundary': 'Ukaribu na mbuga ya wanyama',
    'Livestock Grazing Density': 'Msongamano wa mifugo',
    'Corridor Obstruction': 'Kuzuiwa kwa mapito'
}

def translate_drivers(drivers_str):
    if not drivers_str or drivers_str == 'None':
        return 'Hakuna'
    swahili_drivers = []
    for eng_driver, swa_driver in swahili_drivers_map.items():
        if eng_driver in drivers_str:
            swahili_drivers.append(swa_driver)
    return ", ".join(swahili_drivers) if swahili_drivers else drivers_str

# Generate Text blocks
eng_text = ""
if lvl == 'HIGH':
    eng_text = f"WARNING: High conflict risk detected in {selected_zone_name} due to {selected_zone['primary_drivers']}. Increase kraal security and avoid grazing near park boundaries after dusk."
elif lvl == 'MEDIUM':
    eng_text = f"ADVISORY: Moderate conflict risk in {selected_zone_name} driven by {selected_zone['primary_drivers']}. Remain vigilant at water points."
else:
    eng_text = f"INFO: Low conflict risk in {selected_zone_name}. Standard herding practices apply."

swa_drivers = translate_drivers(selected_zone['primary_drivers'])
swa_text = ""
if lvl == 'HIGH':
    swa_text = f"TAHADHARI: Hatari kubwa ya mzozo na wanyamapori imeonekana {selected_zone_name} kutokana na {swa_drivers}. Imarisha ulinzi wa boma na uepuke kulisha karibu na mbuga usiku."
elif lvl == 'MEDIUM':
    swa_text = f"USHAURI: Hatari ya wastani {selected_zone_name} inayosababishwa na {swa_drivers}. Kuwa mwangalifu kwenye maeneo ya maji."
else:
    swa_text = f"MAELEZO: Hatari ndogo ya mzozo {selected_zone_name}. Endelea na ufugaji kama kawaida."

# Combine based on Language selection
if lang == "English Only":
    advisory_text = eng_text
elif lang == "Swahili (Kiswahili) Only":
    advisory_text = swa_text
else:
    advisory_text = f"{eng_text}\n---\n{swa_text}"

advisory_text = st.text_area("Generated Plain-Language Advisory:", value=advisory_text, height=180)

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
