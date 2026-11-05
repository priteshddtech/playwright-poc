import dashboard.bootstrap  # noqa: F401

import streamlit as st

from dashboard.data.metrics import permanent_fix_recommendations
from dashboard.ui.components import prepare_dashboard, render_page_header
from dashboard.ui.theme import inject_page_theme

inject_page_theme()

render_page_header(
    "Permanent Fix Recommendations",
    "Recurring heals worth fixing in test source code.",
)

outcomes_df, _ = prepare_dashboard()

min_heals = st.slider("Minimum heal count", min_value=1, max_value=20, value=2)
recs = permanent_fix_recommendations(outcomes_df, min_heals=min_heals)

if recs.empty:
    st.info(
        "No recurring patterns yet. Recommendations appear when the same locator is healed "
        f"at least {min_heals} time(s)."
    )
    st.stop()

st.markdown('<div class="panel-title">Recommendations</div>', unsafe_allow_html=True)
st.dataframe(recs, use_container_width=True, hide_index=True)

st.markdown('<div class="panel-title">Suggested source updates</div>', unsafe_allow_html=True)
for _, rec in recs.iterrows():
    with st.expander(f"{rec['element_key']} — healed {rec['heal_count']} times"):
        st.markdown("**Current (typical)**")
        st.code(f'page.locator("{rec["failed_locator"]}")', language="python")
        st.markdown("**Suggested**")
        st.code(rec["suggested_playwright"] or rec["suggested_locator"], language="python")
        st.caption(f"Average confidence when applied: {rec['avg_confidence']}%")
