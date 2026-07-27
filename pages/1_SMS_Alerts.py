import streamlit as st
import pandas as pd
from src.sms_notifier import SMSNotifier
from src.ui_helpers import load_cti_theme
import src.db_contacts as db_contacts
import os

# Apply CTI Theme
load_cti_theme()

st.title(" Community SMS Early Warning Alert")
st.markdown("Dispatch targeted risk advisories to pastoralists and ranger teams.")

if 'df_scored' not in st.session_state:
    st.warning(" No risk data loaded! Please return to the main Risk Map to initialize the dataset.")
    st.stop()

df_scored = st.session_state['df_scored']
zone_names = df_scored['name'].tolist()

# ---------------------------------------------------------
# CONTACT MANAGEMENT UI
# ---------------------------------------------------------
with st.expander("📋 Manage Saved Contacts"):
    col_add, col_view = st.columns([1, 1.5])
    
    with col_add:
        st.subheader("Add Contact")
        with st.form("add_contact_form", clear_on_submit=True):
            new_name = st.text_input("Name")
            new_phone = st.text_input("Phone Number (e.g., +2547...)", placeholder="+254700000000")
            new_zone = st.selectbox("Assign to Zone:", options=zone_names)
            submitted = st.form_submit_button("Save Contact")
            
            if submitted:
                if new_name.strip() and new_phone.strip():
                    db_contacts.add_contact(new_name.strip(), new_phone.strip(), new_zone)
                    st.success(f"Added {new_name}!")
                    st.rerun()
                else:
                    st.error("Name and Phone are required.")
                    
    with col_view:
        st.subheader("Saved Contacts")
        contacts = db_contacts.get_all_contacts()
        if contacts:
            # Create a dataframe for display
            df_contacts = pd.DataFrame(contacts, columns=["ID", "Name", "Phone", "Zone"])
            st.dataframe(df_contacts, hide_index=True, use_container_width=True)
            
            # Simple delete mechanism
            del_id = st.number_input("Delete Contact by ID:", min_value=0, step=1, value=0)
            if st.button("Delete Contact"):
                if del_id > 0:
                    db_contacts.delete_contact(del_id)
                    st.success("Deleted!")
                    st.rerun()
        else:
            st.info("No contacts saved yet.")

st.markdown("---")

# ---------------------------------------------------------
# SMS DISPATCH UI
# ---------------------------------------------------------
selected_zone_name = st.selectbox("Select Conservancy / Zone:", options=zone_names, index=min(7, len(zone_names)-1))
selected_zone = df_scored[df_scored['name'] == selected_zone_name].iloc[0]

lvl = selected_zone['risk_level']
score = selected_zone['risk_score']

st.markdown(f"### {selected_zone_name} - Risk Level: **{lvl}** ({score}%)")
st.markdown(f"**Primary Drivers:** {selected_zone['primary_drivers']}")

lang = st.radio("Select SMS Language:", ["Both (Bilingual)", "English Only", "Swahili (Kiswahili) Only"], horizontal=True)
st.markdown("---")

swahili_drivers_map = {
    'High Vegetation Stress': 'Uhaba mkubwa wa malisho',
    'Water Scarcity': 'Uhaba wa maji',
    'Proximity to National Park Boundary': 'Ukaribu na mbuga ya wanyama',
    'Livestock Grazing Density': 'Msongamano wa mifugo',
    'Corridor Obstruction': 'Kuzuiwa kwa mapito',
    'Exposure (Da) x Hazard': 'Mfiduo na Hatari'
}

def translate_drivers(drivers_str):
    if not drivers_str or drivers_str == 'None':
        return 'Hakuna'
    swahili_drivers = []
    for eng_driver, swa_driver in swahili_drivers_map.items():
        if eng_driver in drivers_str:
            swahili_drivers.append(swa_driver)
    return ", ".join(swahili_drivers) if swahili_drivers else drivers_str

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
    swa_text = f"TAHADHARI: Hatari kubwa ya mzozo imeonekana {selected_zone_name} kutokana na {swa_drivers}. Imarisha ulinzi wa boma na uepuke kulisha karibu na mbuga usiku."
elif lvl == 'MEDIUM':
    swa_text = f"USHAURI: Hatari ya wastani {selected_zone_name} inayosababishwa na {swa_drivers}. Kuwa mwangalifu kwenye maeneo ya maji."
else:
    swa_text = f"MAELEZO: Hatari ndogo ya mzozo {selected_zone_name}. Endelea na ufugaji kama kawaida."

if lang == "English Only":
    advisory_text = eng_text
elif lang == "Swahili (Kiswahili) Only":
    advisory_text = swa_text
else:
    advisory_text = f"{eng_text}\n---\n{swa_text}"

advisory_text = st.text_area("Generated Plain-Language Advisory:", value=advisory_text, height=180)

# Fetch saved contacts for this zone
zone_contacts = db_contacts.get_contacts_by_zone(selected_zone_name)
db_phone_numbers = [contact[1] for contact in zone_contacts]

if db_phone_numbers:
    st.info(f"📁 Loaded **{len(db_phone_numbers)}** saved contacts for {selected_zone_name}.")
else:
    st.info(f"📁 No saved contacts found for {selected_zone_name}.")

phone_input = st.text_area("Additional Manual Numbers (Comma separated):", value="", placeholder="+254712345678, +254700000000")

default_sender = os.getenv("TALKSASA_SENDER_ID", "Talksasa")
sender_input = st.text_input("TalkSasa Sender ID (Originator):", value=default_sender, help="Must be an approved Sender ID on your TalkSasa account")

if st.button(" Dispatch SMS Alert via TalkSasa", type="primary"):
    notifier = SMSNotifier(sender_id=sender_input)
    with st.spinner("Dispatching..."):
        # Combine database numbers and manual numbers
        manual_numbers = [num.strip() for num in phone_input.split(",") if num.strip()]
        all_numbers = list(set(db_phone_numbers + manual_numbers))
        
        if not all_numbers:
            st.error("No phone numbers provided to dispatch.")
        elif len(all_numbers) > 5:
            st.error(f"🛑 **Hackathon Demo Limit:** You are attempting to dispatch to {len(all_numbers)} numbers. To prevent API abuse during the demo, the system is capped at **5 numbers** per dispatch.")
        else:
            results = notifier.send_bulk_alerts(all_numbers, advisory_text, selected_zone['name'])
            
            success_count = sum(1 for r in results if r['status'] in ['SUCCESS', 'FALLBACK_SANDBOX'])
            if success_count > 0:
                st.success(f" Successfully dispatched {success_count} / {len(all_numbers)} SMS Alerts!")
                with st.expander("View Dispatch Details"):
                    st.json(results)
            else:
                st.error(f" Failed to dispatch alerts.")
                if results:
                    st.error(f" Error: {results[0].get('error')}")
