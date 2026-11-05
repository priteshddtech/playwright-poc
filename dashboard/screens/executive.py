from __future__ import annotations

import streamlit as st

from dashboard.data.metrics import compute_kpis, daily_failure_trends, daily_heal_success_rate
from dashboard.ui.components import prepare_dashboard, render_filters, render_kpi_row, render_page_header


def render() -> None:
    render_page_header(
        "Executive Summary",
        "Automation health, healing outcomes, and emerging failure trends.",
    )

    outcomes_df, _stability = prepare_dashboard()
    filtered = render_filters(outcomes_df)
    kpis = compute_kpis(filtered)
    render_kpi_row(kpis)

    st.divider()
    st.markdown('<div class="panel-title">Trends</div>', unsafe_allow_html=True)
    if filtered.empty:
        st.warning("No healing outcomes yet. Run pytest or the visible demo to populate the audit log.")
    else:
        trend_col1, trend_col2 = st.columns(2)
        failures_by_day = daily_failure_trends(filtered)
        if not failures_by_day.empty:
            pivot = failures_by_day.pivot_table(
                index="date",
                columns="failure_category_label",
                values="count",
                fill_value=0,
                aggfunc="sum",
            )
            with trend_col1:
                st.caption("Failures by category")
                st.bar_chart(pivot)
        success = daily_heal_success_rate(filtered)
        if not success.empty:
            with trend_col2:
                st.caption("Heal success rate (%)")
                st.line_chart(success.set_index("date")["success_rate"])
