import dashboard.bootstrap  # noqa: F401

import streamlit as st

from dashboard.ui.components import prepare_dashboard, render_page_header
from dashboard.ui.theme import inject_page_theme

inject_page_theme()

render_page_header(
    "Locator Stability Analysis",
    "Elements that fail and heal most often.",
)

outcomes_df, stability_df = prepare_dashboard()

if stability_df.empty:
    st.warning("No stability data from SQLite or audit log.")
    st.stop()

top_n = st.slider("Top N locators", min_value=5, max_value=50, value=15)
show = stability_df.head(top_n)

display = show[
    [c for c in ("element_key", "failed_locator", "heal_count", "locator_label") if c in show.columns]
].rename(
    columns={
        "element_key": "Element",
        "failed_locator": "Locator",
        "heal_count": "Heal count",
    }
)

st.markdown('<div class="panel-title">Most unstable elements</div>', unsafe_allow_html=True)
st.dataframe(display, use_container_width=True, hide_index=True)

chart_df = (
    show.set_index("locator_label")[["heal_count"]]
    if "locator_label" in show.columns
    else show.set_index("failed_locator")[["heal_count"]]
)
st.markdown('<div class="panel-title">Heal frequency</div>', unsafe_allow_html=True)
st.bar_chart(chart_df)
