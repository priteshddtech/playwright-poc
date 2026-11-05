from __future__ import annotations

from typing import Any

import pandas as pd

from dashboard.data.models import locator_dict_to_display


def compute_kpis(df: pd.DataFrame) -> dict[str, int]:
    if df.empty:
        return {
            "total_executions": 0,
            "passed": 0,
            "failed": 0,
            "auto_healed": 0,
            "ai_healed": 0,
            "pending_review": 0,
            "manual_fixes_required": 0,
            "heal_attempts": 0,
        }
    heal_attempts = len(df)
    total_executions = int(df["execution_id"].nunique()) if "execution_id" in df.columns else heal_attempts
    passed = int((df["healing_succeeded"] == True).sum())  # noqa: E712
    failed = int((df["healing_succeeded"] == False).sum())  # noqa: E712
    auto_healed = int(((df["healing_succeeded"] == True) & (~df["solved_by_llm"])).sum())  # noqa: E712
    ai_healed = int((df["solved_by_llm"] == True).sum())  # noqa: E712
    status = df["healing_status"] if "healing_status" in df.columns else pd.Series(dtype=str)
    pending_review = int((status == "pending_review").sum())
    manual_fixes = int(
        ((df["healing_succeeded"] == False) & (status != "pending_review")).sum()  # noqa: E712
    )
    return {
        "total_executions": total_executions,
        "passed": passed,
        "failed": failed,
        "auto_healed": auto_healed,
        "ai_healed": ai_healed,
        "pending_review": pending_review,
        "manual_fixes_required": manual_fixes,
        "heal_attempts": heal_attempts,
    }


def filter_outcomes(
    df: pd.DataFrame,
    *,
    test_names: list[str] | None = None,
    environments: list[str] | None = None,
    start_date: pd.Timestamp | None = None,
    end_date: pd.Timestamp | None = None,
) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    if test_names and "test_name" in out.columns:
        out = out[out["test_name"].isin(test_names)]
    if environments and "environment" in out.columns:
        out = out[out["environment"].isin(environments)]
    if start_date is not None and "timestamp" in out.columns:
        out = out[out["timestamp"] >= start_date]
    if end_date is not None and "timestamp" in out.columns:
        out = out[out["timestamp"] <= end_date]
    return out


def daily_failure_trends(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "timestamp" not in df.columns:
        return pd.DataFrame()
    tmp = df.copy()
    tmp["date"] = tmp["timestamp"].dt.floor("D")
    label_col = "failure_category_label" if "failure_category_label" in tmp.columns else "failure_category"
    counts = (
        tmp.groupby(["date", label_col], dropna=False)
        .size()
        .reset_index(name="count")
        .rename(columns={label_col: "failure_category_label"})
    )
    return counts


def daily_heal_success_rate(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "timestamp" not in df.columns:
        return pd.DataFrame()
    tmp = df.copy()
    tmp["date"] = tmp["timestamp"].dt.floor("D")
    grouped = tmp.groupby("date", dropna=False)["healing_succeeded"].agg(["sum", "count"]).reset_index()
    grouped["success_rate"] = grouped["sum"] / grouped["count"].clip(lower=1) * 100.0
    return grouped


def permanent_fix_recommendations(df: pd.DataFrame, min_heals: int = 2) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            columns=[
                "element_key",
                "failed_locator",
                "heal_count",
                "suggested_locator",
                "suggested_playwright",
                "avg_confidence",
            ]
        )
    healed = df[df["healing_succeeded"] == True].copy()  # noqa: E712
    if healed.empty:
        return pd.DataFrame(
            columns=[
                "element_key",
                "failed_locator",
                "heal_count",
                "suggested_locator",
                "suggested_playwright",
                "avg_confidence",
            ]
        )

    rows: list[dict[str, Any]] = []
    for (element_key, failed_locator), group in healed.groupby(["element_key", "failed_locator"], dropna=False):
        heal_count = len(group)
        if heal_count < min_heals:
            continue
        applied_str = group["applied_locator_str"].mode()
        suggested = applied_str.iloc[0] if len(applied_str) else ""
        sample = group.iloc[0].get("applied_locator")
        if isinstance(sample, dict):
            suggested_pw = locator_dict_to_display(sample)
        else:
            suggested_pw = suggested
        avg_conf = float(group["confidence"].mean()) if "confidence" in group.columns else 0.0
        rows.append(
            {
                "element_key": element_key,
                "failed_locator": failed_locator,
                "heal_count": heal_count,
                "suggested_locator": suggested,
                "suggested_playwright": suggested_pw,
                "avg_confidence": round(avg_conf, 2),
            }
        )
    if not rows:
        return pd.DataFrame(
            columns=[
                "element_key",
                "failed_locator",
                "heal_count",
                "suggested_locator",
                "suggested_playwright",
                "avg_confidence",
            ]
        )
    return pd.DataFrame(rows).sort_values("heal_count", ascending=False)


def get_outcome_by_key(df: pd.DataFrame, execution_id: str, timestamp: str | None = None) -> dict[str, Any] | None:
    if df.empty or not execution_id:
        return None
    subset = df[df["execution_id"] == execution_id]
    if timestamp and "timestamp" in subset.columns:
        ts = pd.to_datetime(timestamp, utc=True)
        match = subset[subset["timestamp"] == ts]
        if not match.empty:
            return match.iloc[0].to_dict()
    if subset.empty:
        return None
    return subset.sort_values("timestamp", ascending=False).iloc[0].to_dict()
