import streamlit as st
import os

def load_cti_theme():
    """Loads the global Cyber Threat Intelligence (CTI) CSS into the Streamlit app."""
    css_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'style.css')
    try:
        with open(css_path, 'r', encoding='utf-8') as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"Failed to load CTI theme: {e}")

def cti_metric_card(title, value, subtext="", severity="normal"):
    """
    Renders a styled CTI metric card.
    severity can be 'normal', 'warning', or 'critical'.
    """
    html = f'''
    <div class="cti-card {severity}">
        <h4>{title}</h4>
        <div class="value">{value}</div>
        <div class="subtext">{subtext}</div>
    </div>
    '''
    st.markdown(html, unsafe_allow_html=True)
