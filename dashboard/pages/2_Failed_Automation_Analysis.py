import dashboard.bootstrap  # noqa: F401

import streamlit as st

from dashboard.ui.components import prepare_dashboard, render_page_header, select_outcome
from dashboard.ui.theme import inject_page_theme

inject_page_theme()

render_page_header(
    "Failed Automation Analysis",
    "Failed tests, application pages, and failure categories.",
)

outcomes_df, _ = prepare_dashboard()

if outcomes_df.empty:
    st.warning("No data in audit log.")
    st.stop()

failures = outcomes_df[outcomes_df["healing_succeeded"] == False].copy()  # noqa: E712
if failures.empty:
    st.success("No failed healing outcomes in the log.")
    st.dataframe(
        outcomes_df[
            [
                c
                for c in (
                    "timestamp",
                    "test_name",
                    "page_label",
                    "failure_category_label",
                    "execution_id",
                )
                if c in outcomes_df.columns
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )
    st.stop()

display_cols = [
    c
    for c in (
        "timestamp",
        "test_name",
        "page_label",
        "failure_category_label",
        "failed_locator",
        "execution_id",
    )
    if c in failures.columns
]
table = failures.sort_values("timestamp", ascending=False)[display_cols].rename(
    columns={
        "test_name": "Test",
        "page_label": "Page",
        "failure_category_label": "Failure",
        "failed_locator": "Failed locator",
        "execution_id": "Execution ID",
    }
)

st.markdown('<div class="panel-title">Failures</div>', unsafe_allow_html=True)
st.dataframe(table, use_container_width=True, hide_index=True)

st.markdown('<div class="panel-title">Investigate</div>', unsafe_allow_html=True)
labels: list[str] = []
rows: list[dict] = []
for _, row in failures.sort_values("timestamp", ascending=False).iterrows():
    ts = row.get("timestamp")
    ts_str = ts.isoformat() if ts is not None else ""
    label = f"{row.get('test_name', '?')} · {row.get('page_label', '?')} · {row.get('failure_category_label', '?')}"
    labels.append(label)
    rows.append({"execution_id": row["execution_id"], "timestamp": ts_str})

inv_col1, inv_col2 = st.columns([3, 1])
with inv_col1:
    choice = st.selectbox("Select a failure", range(len(labels)), format_func=lambda i: labels[i], label_visibility="collapsed")
with inv_col2:
    if st.button("Open investigation", type="primary", use_container_width=True):
        selected = rows[choice]
        select_outcome(selected["execution_id"], selected["timestamp"] or None)
        st.switch_page("pages/3_Failure_Investigation.py")
