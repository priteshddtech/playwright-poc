from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from dashboard.data.models import flatten_locator_fields


def read_healing_outcomes(audit_log_path: Path) -> list[dict[str, Any]]:
    if not audit_log_path.is_file():
        return []
    outcomes: list[dict[str, Any]] = []
    with audit_log_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("event_type") != "healing_outcome":
                continue
            outcomes.append(flatten_locator_fields(record))
    return outcomes


def outcomes_to_dataframe(outcomes: list[dict[str, Any]]) -> pd.DataFrame:
    if not outcomes:
        return pd.DataFrame()
    df = pd.DataFrame(outcomes)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    for col in ("healing_succeeded", "solved_by_llm", "llm_invoked"):
        if col in df.columns:
            df[col] = df[col].fillna(False).astype(bool)
    return df


def load_outcomes_dataframe(audit_log_path: Path) -> pd.DataFrame:
    return outcomes_to_dataframe(read_healing_outcomes(audit_log_path))


def audit_file_mtime(audit_log_path: Path) -> float:
    if audit_log_path.is_file():
        return audit_log_path.stat().st_mtime
    return 0.0
