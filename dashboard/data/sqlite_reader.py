from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


def load_healing_event_counts(db_path: Path) -> pd.DataFrame:
    if not db_path.is_file():
        return pd.DataFrame(columns=["element_key", "failed_locator", "heal_count"])
    query = """
        SELECT
            element_key,
            failed_locator,
            COUNT(*) AS heal_count
        FROM healing_events
        WHERE healed_locator IS NOT NULL AND healed_locator != ''
        GROUP BY element_key, failed_locator
        ORDER BY heal_count DESC
    """
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql_query(query, conn)


def load_locator_stability(db_path: Path, limit: int = 50) -> pd.DataFrame:
    df = load_healing_event_counts(db_path)
    if df.empty:
        return df
    df["locator_label"] = df["failed_locator"].astype(str)
    return df.head(limit)


def stability_from_outcomes(outcomes_df: pd.DataFrame) -> pd.DataFrame:
    if outcomes_df.empty:
        return pd.DataFrame(columns=["element_key", "failed_locator", "heal_count", "locator_label"])
    healed = outcomes_df[outcomes_df["healing_succeeded"] == True]  # noqa: E712
    if healed.empty:
        return pd.DataFrame(columns=["element_key", "failed_locator", "heal_count", "locator_label"])
    grouped = (
        healed.groupby(["element_key", "failed_locator"], dropna=False)
        .size()
        .reset_index(name="heal_count")
        .sort_values("heal_count", ascending=False)
    )
    grouped["locator_label"] = grouped["failed_locator"].astype(str)
    return grouped
