from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from dashboard.config import DashboardSettings, get_dashboard_settings
from dashboard.data.loaders import load_dashboard_data
from dashboard.data.models import locator_dict_to_display


def init_session_state() -> None:
    if "selected_execution_id" not in st.session_state:
        st.session_state.selected_execution_id = None
    if "selected_timestamp" not in st.session_state:
        st.session_state.selected_timestamp = None


def select_outcome(execution_id: str, timestamp: str | None = None) -> None:
    st.session_state.selected_execution_id = execution_id
    st.session_state.selected_timestamp = timestamp


def prepare_dashboard(settings: DashboardSettings | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load cached audit/SQLite data. Refresh control lives in the page header."""
    settings = settings or get_dashboard_settings()
    init_session_state()
    return load_dashboard_data(settings)


def render_page_header(title: str, subtitle: str) -> None:
    _, refresh_col = st.columns([11, 1])
    with refresh_col:
        if st.button("Refresh", use_container_width=True, help="Reload audit data"):
            st.cache_data.clear()
            st.rerun()
    st.markdown(
        f'<div class="dashboard-header"><h1>{title}</h1><p>{subtitle}</p></div>',
        unsafe_allow_html=True,
    )


def render_kpi_row(kpis: dict[str, int]) -> None:
    st.markdown('<div class="panel-title">Overview</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total executions", kpis["total_executions"], help="Distinct runs with healing outcomes")
    c2.metric("Heal attempts", kpis["heal_attempts"])
    c3.metric("Passed (healed)", kpis["passed"])
    c4.metric("Failed", kpis["failed"])
    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Auto healed", kpis["auto_healed"])
    c6.metric("AI healed", kpis["ai_healed"])
    c7.metric("Pending review", kpis["pending_review"])
    c8.metric("Manual fixes required", kpis["manual_fixes_required"])


def resolve_artifact_path(raw_path: str | None, artifacts_dir: Path) -> Path | None:
    if not raw_path:
        return None
    path = Path(raw_path)
    if path.is_file():
        return path
    candidate = artifacts_dir / path.name
    if candidate.is_file():
        return candidate
    try:
        rel = path.relative_to(artifacts_dir)
        full = artifacts_dir / rel
        if full.is_file():
            return full
    except ValueError:
        pass
    return path if path.is_file() else None


def render_artifact_panel(row: dict[str, Any], settings: DashboardSettings | None = None) -> None:
    settings = settings or get_dashboard_settings()
    artifacts_dir = settings.resolved_artifacts_dir()
    screenshot = resolve_artifact_path(row.get("screenshot_path"), artifacts_dir)
    html_path = resolve_artifact_path(row.get("html_snapshot_path"), artifacts_dir)
    st.markdown('<div class="panel-title">Artifacts</div>', unsafe_allow_html=True)
    art_col1, art_col2 = st.columns([2, 1])
    with art_col1:
        if screenshot and screenshot.is_file():
            st.image(str(screenshot), use_container_width=True)
        else:
            st.caption("Screenshot not available.")
    with art_col2:
        if html_path and html_path.is_file():
            st.download_button(
                "Download HTML snapshot",
                data=html_path.read_bytes(),
                file_name=html_path.name,
                mime="text/html",
                use_container_width=True,
            )
        else:
            st.caption("HTML snapshot not available.")


def format_locator_for_display(locator: dict[str, Any] | None) -> str:
    return locator_dict_to_display(locator)


def render_filters(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    tests: list[str] = []
    envs: list[str] = []
    if "test_name" in df.columns:
        tests = sorted(df["test_name"].dropna().unique().tolist())
    if "environment" in df.columns:
        envs = sorted(df["environment"].dropna().unique().tolist())
    min_ts = df["timestamp"].min() if "timestamp" in df.columns else None
    max_ts = df["timestamp"].max() if "timestamp" in df.columns else None
    selected_tests = tests
    selected_envs = envs
    date_range: tuple | list = ()
    with st.expander("Filters", expanded=False):
        col1, col2, col3 = st.columns(3)
        selected_tests = col1.multiselect("Test", tests, default=tests)
        selected_envs = col2.multiselect("Environment", envs, default=envs)
        date_range = col3.date_input(
            "Date range",
            value=(min_ts.date(), max_ts.date()) if min_ts is not None and max_ts is not None else (),
            disabled=min_ts is None,
        )
    filtered = df.copy()
    if selected_tests and "test_name" in filtered.columns:
        filtered = filtered[filtered["test_name"].isin(selected_tests)]
    if selected_envs and "environment" in filtered.columns:
        filtered = filtered[filtered["environment"].isin(selected_envs)]
    if isinstance(date_range, tuple) and len(date_range) == 2 and "timestamp" in filtered.columns:
        start, end = date_range
        start_ts = pd.Timestamp(start, tz="UTC")
        end_ts = pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)
        filtered = filtered[(filtered["timestamp"] >= start_ts) & (filtered["timestamp"] < end_ts)]
    return filtered


def render_detail_grid(items: list[tuple[str, str]]) -> None:
    """Two-column label / value panel."""
    with st.container(border=True):
        left, right = st.columns(2)
        half = (len(items) + 1) // 2
        for col, chunk in ((left, items[:half]), (right, items[half:])):
            with col:
                for label, value in chunk:
                    st.markdown(f"**{label}**")
                    st.markdown(value)


def require_selection_message() -> None:
    st.info("Select a failure from **Failed Automation Analysis** to view details.")
    if st.button("Go to Failed Automation Analysis", type="primary"):
        st.switch_page("pages/2_Failed_Automation_Analysis.py")
