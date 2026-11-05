import dashboard.bootstrap  # noqa: F401

import streamlit as st

from dashboard.screens import executive
from dashboard.ui.theme import setup_page

setup_page(page_title="App")

pg = st.navigation(
    [
        st.Page(executive.render, title="App", default=True),
        st.Page("pages/2_Failed_Automation_Analysis.py", title="Failed Automation Analysis"),
        st.Page("pages/3_Failure_Investigation.py", title="Failure Investigation"),
        st.Page("pages/4_AI_Healing_Details.py", title="AI Healing Details"),
        st.Page("pages/5_Permanent_Fix_Recommendations.py", title="Permanent Fix Recommendations"),
        st.Page("pages/6_Locator_Stability_Analysis.py", title="Locator Stability Analysis"),
    ]
)
pg.run()
