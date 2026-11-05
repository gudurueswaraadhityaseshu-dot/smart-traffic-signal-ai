"""Smart Traffic AI - entry point. Defines the grouped navigation menu."""

import os

import streamlit as st

from src.dashboard.style import apply_style

st.set_page_config(page_title="Smart Traffic AI", page_icon="🚦", layout="wide")
apply_style()

LOGO = os.path.join("assets", "logo.svg")
if os.path.exists(LOGO):
    try:
        st.logo(LOGO, size="large")
    except TypeError:  # older Streamlit versions have no size option
        st.logo(LOGO)

# (file, menu name, icon). The first item is the page that opens first.
MENU = {
    "Operations": [
        ("views/traffic_dashboard.py", "Traffic Control Center", ":material/traffic:"),
        ("views/vehicle_detection.py", "Vehicle Detection", ":material/videocam:"),
    ],
    "Analytics": [
        ("views/performance_analytics.py", "Performance Analytics", ":material/monitoring:"),
        ("views/model_evaluation.py", "Model Evaluation", ":material/fact_check:"),
    ],
}

sections = {}
first_page = True
for section, items in MENU.items():
    pages = []
    for path, title, icon in items:
        if os.path.exists(path):  # a missing file is left out instead of crashing
            pages.append(st.Page(path, title=title, icon=icon, default=first_page))
            first_page = False
    if pages:
        sections[section] = pages

st.navigation(sections).run()