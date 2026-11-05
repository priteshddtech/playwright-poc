from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from dashboard.config import DashboardSettings, get_dashboard_settings
from dashboard.data.audit_reader import audit_file_mtime, load_outcomes_dataframe
from dashboard.data.sqlite_reader import load_locator_stability, stability_from_outcomes


@st.cache_data(ttl=60)
def cached_outcomes(audit_path_str: str, mtime: float) -> pd.DataFrame:
    _ = mtime
    return load_outcomes_dataframe(Path(audit_path_str))


@st.cache_data(ttl=60)
def cached_sqlite_stability(sqlite_path_str: str, mtime: float) -> pd.DataFrame:
    _ = mtime
    return load_locator_stability(Path(sqlite_path_str))


def sqlite_mtime(path: Path) -> float:
    if path.is_file():
        return path.stat().st_mtime
    return 0.0


def load_dashboard_data(settings: DashboardSettings | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    settings = settings or get_dashboard_settings()
    audit_path = settings.resolved_audit_log_path()
    sqlite_path = settings.resolved_sqlite_path()
    outcomes = cached_outcomes(str(audit_path), audit_file_mtime(audit_path))
    stability_db = cached_sqlite_stability(str(sqlite_path), sqlite_mtime(sqlite_path))
    if stability_db.empty and not outcomes.empty:
        stability_db = stability_from_outcomes(outcomes)
    return outcomes, stability_db
