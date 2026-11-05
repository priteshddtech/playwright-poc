import dashboard.bootstrap  # noqa: F401

import streamlit as st

from dashboard.data.metrics import get_outcome_by_key
from dashboard.ui.components import (
    format_locator_for_display,
    init_session_state,
    prepare_dashboard,
    render_page_header,
    require_selection_message,
)
from dashboard.ui.theme import inject_page_theme

inject_page_theme()

render_page_header(
    "AI Healing Details",
    "LLM proposals, confidence, and applied locators.",
)

init_session_state()
outcomes_df, _ = prepare_dashboard()

execution_id = st.session_state.get("selected_execution_id")
timestamp = st.session_state.get("selected_timestamp")

st.markdown('<div class="panel-title">Recent AI-related outcomes</div>', unsafe_allow_html=True)
if not outcomes_df.empty:
    ai_rows = outcomes_df[
        (outcomes_df["llm_invoked"] == True)  # noqa: E712
        | (outcomes_df["solved_by_llm"] == True)  # noqa: E712
        | (outcomes_df["llm_proposal"].notna() if "llm_proposal" in outcomes_df.columns else False)
    ]
    if not ai_rows.empty:
        st.dataframe(
            ai_rows[
                [
                    c
                    for c in (
                        "timestamp",
                        "test_name",
                        "failed_locator",
                        "solved_by_llm",
                        "confidence",
                        "healing_status",
                    )
                    if c in ai_rows.columns
                ]
            ].sort_values("timestamp", ascending=False),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.caption("No LLM-involved healings in the audit log yet.")

st.divider()
st.markdown('<div class="panel-title">Selected failure</div>', unsafe_allow_html=True)

if not execution_id:
    require_selection_message()
    st.stop()

row = get_outcome_by_key(outcomes_df, execution_id, timestamp)
if row is None:
    st.error("Selected outcome not found.")
    st.stop()

st.markdown(f"**Original locator:** `{row.get('failed_locator', '—')}`")

llm = row.get("llm_proposal")
if isinstance(llm, dict):
    st.markdown("**AI analysis**")
    st.write(llm.get("reason") or row.get("summary") or "—")
    st.markdown("**Suggested locator**")
    st.code(format_locator_for_display(llm), language="python")
else:
    st.write(row.get("summary") or "No LLM proposal for this outcome.")
    applied = row.get("applied_locator")
    if isinstance(applied, dict):
        st.markdown("**Applied locator (deterministic / history)**")
        st.code(format_locator_for_display(applied), language="python")

c1, c2, c3 = st.columns(3)
c1.metric("Confidence", f"{row.get('confidence', 0):.1f}%")
c2.metric("Healing method", row.get("healing_method", "—"))
c3.metric("Solved by LLM", "Yes" if row.get("solved_by_llm") else "No")
st.caption(f"Healing status: {row.get('healing_status', '—')}")
if row.get("llm_error"):
    st.error(f"LLM error: {row['llm_error']}")
