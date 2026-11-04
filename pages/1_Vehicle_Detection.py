"""Streamlit shows every file in the pages/ folder as a page in the sidebar."""

import streamlit as st

from src.dashboard.detection_view import render_detection_page
from src.dashboard.style import apply_style

st.set_page_config(page_title="Vehicle Detection", page_icon="🚗", layout="wide")
apply_style()
render_detection_page()