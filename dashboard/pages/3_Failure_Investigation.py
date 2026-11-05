import dashboard.bootstrap  # noqa: F401

import streamlit as st

from dashboard.data.metrics import get_outcome_by_key
from dashboard.ui.components import (
    init_session_state,
    prepare_dashboard,
    render_artifact_panel,
    render_detail_grid,
    render_page_header,
    require_selection_message,
)
from dashboard.ui.theme import inject_page_theme

inject_page_theme()

render_page_header(
    "Failure Investigation",
    "Locator context, failure reason, and captured artifacts.",
)

init_session_state()
outcomes_df, _ = prepare_dashboard()

execution_id = st.session_state.get("selected_execution_id")
timestamp = st.session_state.get("selected_timestamp")

if not execution_id:
    require_selection_message()
    st.stop()

row = get_outcome_by_key(outcomes_df, execution_id, timestamp)
if row is None:
    st.error("Selected outcome not found. It may have been rotated out of the audit log.")
    st.stop()

render_detail_grid(
    [
        ("Test", row.get("test_name", "—")),
        ("Failed locator", f"`{row.get('failed_locator', '—')}`"),
        ("Page", str(row.get("page_label") or row.get("page_key") or "—")),
        ("Reason", str(row.get("failure_category_label", "—"))),
        ("Element", str(row.get("element_key", "—"))),
        ("Healing status", str(row.get("healing_status", "—"))),
        ("Description", str(row.get("element_description", "—"))),
        ("Execution ID", f"`{row.get('execution_id', '—')}`"),
    ]
)

with st.expander("Original error", expanded=False):
    st.code(row.get("original_error") or "—", language="text")

with st.expander("Healing summary", expanded=True):
    st.write(row.get("summary") or "—")

render_artifact_panel(row)

if st.button("View AI healing details", type="primary"):
    st.switch_page("pages/4_AI_Healing_Details.py")
