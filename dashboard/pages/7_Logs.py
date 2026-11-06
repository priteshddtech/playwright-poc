import dashboard.bootstrap  # noqa: F401

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from dashboard.config import get_dashboard_settings
from dashboard.data.audit_reader import audit_file_mtime, read_audit_records
from dashboard.ui.components import render_page_header
from dashboard.ui.theme import inject_page_theme


def _sanitize_for_json(val: object) -> object:
    """Convert a dataframe cell to a JSON-safe value (scalars only for pd.isna)."""
    if isinstance(val, pd.Timestamp):
        return val.isoformat()
    if isinstance(val, (dict, list, str, bool, int)):
        return val
    if isinstance(val, float):
        return None if pd.isna(val) else val
    if val is None:
        return None
    try:
        import numpy as np

        if isinstance(val, np.ndarray):
            return val.tolist()
    except ImportError:
        pass
    try:
        if pd.isna(val):
            return None
    except (ValueError, TypeError):
        pass
    return val


inject_page_theme()

render_page_header(
    "Logs",
    "Browse raw JSON audit events from the healing log.",
)


@st.cache_data(ttl=60)
def cached_audit_records(audit_path_str: str, mtime: float) -> list[dict]:
    _ = mtime
    return read_audit_records(Path(audit_path_str))


settings = get_dashboard_settings()
audit_path = settings.resolved_audit_log_path()
records = cached_audit_records(str(audit_path), audit_file_mtime(audit_path))

st.caption(f"Source: `{audit_path}`")

if not audit_path.is_file():
    st.warning("Audit log file not found. Run tests with self-healing to generate `artifacts/logs/healing_audit.jsonl`.")
    st.stop()

if not records:
    st.info("Log file exists but contains no JSON records yet.")
    st.stop()

df = pd.DataFrame(records)
if "timestamp" in df.columns:
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")

event_types = sorted(df["event_type"].dropna().astype(str).unique()) if "event_type" in df.columns else []
search_default = st.session_state.get("logs_search", "")

filter_col1, filter_col2 = st.columns([2, 3])
with filter_col1:
    selected_types = st.multiselect(
        "Event type",
        event_types,
        default=event_types,
        placeholder="All types",
    )
with filter_col2:
    search = st.text_input(
        "Search",
        value=search_default,
        placeholder="execution_id, test_name, element_key…",
    )
    st.session_state.logs_search = search

filtered = df.copy()
if selected_types and "event_type" in filtered.columns:
    filtered = filtered[filtered["event_type"].astype(str).isin(selected_types)]
if search.strip():
    needle = search.strip().lower()
    mask = pd.Series(False, index=filtered.index)
    for col in ("execution_id", "test_name", "element_key", "event_type"):
        if col in filtered.columns:
            mask |= filtered[col].astype(str).str.lower().str.contains(needle, na=False)
    filtered = filtered[mask]

st.metric("Matching events", len(filtered), help=f"{len(records)} total lines in file")

display_cols = [
    c
    for c in (
        "timestamp",
        "event_type",
        "execution_id",
        "test_name",
        "element_key",
        "healing_succeeded",
        "failure_category_label",
    )
    if c in filtered.columns
]
table = filtered.sort_values("timestamp", ascending=False) if "timestamp" in filtered.columns else filtered
st.dataframe(
    table[display_cols] if display_cols else table,
    use_container_width=True,
    hide_index=True,
)

st.markdown('<div class="panel-title">Event detail</div>', unsafe_allow_html=True)

sorted_records = filtered.sort_values("timestamp", ascending=False) if "timestamp" in filtered.columns else filtered

labels: list[str] = []
for _, row in sorted_records.iterrows():
    ts = row.get("timestamp")
    ts_str = ts.isoformat() if pd.notna(ts) else "—"
    et = row.get("event_type", "?")
    ex = row.get("execution_id", "—")
    labels.append(f"{ts_str} · {et} · {ex}")

if not labels:
    st.info("No events match the current filters.")
    st.stop()

choice = st.selectbox("Select an event", range(len(labels)), format_func=lambda i: labels[i])

record = {
    key: _sanitize_for_json(val)
    for key, val in sorted_records.iloc[choice].to_dict().items()
}

st.json(record)

pretty = json.dumps(record, indent=2, default=str)
st.download_button(
    "Download event JSON",
    data=pretty,
    file_name="audit_event.json",
    mime="application/json",
)

with st.expander("Download filtered log (JSONL)", expanded=False):
    lines = "\n".join(json.dumps(r, default=str) for r in sorted_records.to_dict(orient="records"))
    st.download_button(
        "Download JSONL",
        data=lines,
        file_name="healing_audit_filtered.jsonl",
        mime="application/x-ndjson",
        key="download_jsonl",
    )
