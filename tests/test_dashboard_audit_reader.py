from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from dashboard.data.audit_reader import load_outcomes_dataframe, read_healing_outcomes
from dashboard.data.metrics import compute_kpis, permanent_fix_recommendations
from dashboard.data.models import derive_page_label, locator_dict_to_display


def test_read_healing_outcomes_filters_event_type(tmp_path: Path) -> None:
    log = tmp_path / "healing_audit.jsonl"
    log.write_text(
        "\n".join(
            [
                json.dumps({"event_type": "healing_started", "execution_id": "a"}),
                json.dumps(
                    {
                        "event_type": "healing_outcome",
                        "execution_id": "exec-1",
                        "test_name": "t1",
                        "element_key": "save_button",
                        "page_key": "form1_changed.html",
                        "healing_succeeded": True,
                        "solved_by_llm": False,
                        "healing_status": "success",
                        "failed_locator": "#save",
                        "applied_locator": {
                            "strategy": "role",
                            "locator": "role:button:Save",
                            "role": "button",
                            "name": "Save",
                        },
                        "confidence": 90.0,
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )
    outcomes = read_healing_outcomes(log)
    assert len(outcomes) == 1
    assert outcomes[0]["execution_id"] == "exec-1"
    assert outcomes[0]["applied_locator_str"].startswith("page.get_by_role")
    assert outcomes[0]["page_label"] == "Form1 Changed"


def test_compute_kpis_and_recommendations(tmp_path: Path) -> None:
    rows = []
    for i in range(3):
        rows.append(
            {
                "execution_id": f"e{i}",
                "healing_succeeded": True,
                "solved_by_llm": False,
                "healing_status": "success",
                "element_key": "btn",
                "failed_locator": "#x",
                "applied_locator_str": 'page.locator("role:button:OK")',
                "confidence": 88.0,
            }
        )
    rows.append(
        {
            "execution_id": "e-fail",
            "healing_succeeded": False,
            "solved_by_llm": False,
            "healing_status": "failed",
            "element_key": "btn",
            "failed_locator": "#y",
            "confidence": 0.0,
        }
    )
    df = pd.DataFrame(rows)
    kpis = compute_kpis(df)
    assert kpis["total_executions"] == 4
    assert kpis["passed"] == 3
    assert kpis["failed"] == 1
    assert kpis["auto_healed"] == 3

    recs = permanent_fix_recommendations(df, min_heals=2)
    assert len(recs) == 1
    assert recs.iloc[0]["heal_count"] == 3


def test_locator_display_css() -> None:
    assert locator_dict_to_display({"strategy": "css", "locator": "#saveButton"}) == 'page.locator("#saveButton")'


def test_derive_page_label_from_description() -> None:
    label = derive_page_label(
        {"element_key": "x", "element_description": "Submit button for employee registration form"}
    )
    assert "employee" in label.lower()
