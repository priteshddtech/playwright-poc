from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import Page, expect


def _fill_line_row(
    page: Page,
    row_index: int,
    *,
    name: str,
    category_label: str,
    status_label: str,
    priority_value: str,
) -> None:
    row = page.locator(f"#lineItemsBody tr[data-row-index='{row_index}']")
    row.locator(".item-name").fill(name)
    row.locator(".item-category").select_option(label=category_label)
    row.locator(".item-status").select_option(label=status_label)
    row.locator(".item-priority").select_option(value=priority_value)


def _read_audit_events(audit_log: Path) -> list[dict]:
    if not audit_log.is_file():
        return []
    return [
        json.loads(line)
        for line in audit_log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_cascade_complex_form_self_heals_stale_locators(
    self_healing_page, test_settings, html_dir: Path
) -> None:
    """Stale locators from v1 markup; heuristics/fuzzy/LLM recover on the changed cascade form."""
    form_uri = (html_dir / "form_cascade_line_items_changed.html").resolve().as_uri()
    page = self_healing_page.page
    page.goto(form_uri)
    shp = self_healing_page

    shp.select_option(
        "#cascadeRegion",
        element_key="cascade_region_select",
        description="Region dropdown on line-item cascade configuration form",
        value="americas",
    )
    shp.select_option(
        "#cascadeDepartment",
        element_key="cascade_department_select",
        description="Department dropdown on line-item cascade configuration form",
        value="sales",
    )
    shp.select_option(
        "#cascadeTeam",
        element_key="cascade_team_select",
        description="Team dropdown on line-item cascade configuration form",
        value="field-sales",
    )
    shp.click(
        "#btnRevealTable",
        element_key="cascade_build_grid",
        description="Build line-item grid button on cascade configuration form",
    )
    expect(page.locator("#lineItemsPanel")).to_be_visible()

    _fill_line_row(
        page,
        1,
        name="Laptop bundle",
        category_label="Hardware",
        status_label="Draft",
        priority_value="high",
    )

    shp.click(
        "#btnAddRow",
        element_key="cascade_add_row",
        description="Add row button on cascade line-item grid",
    )
    _fill_line_row(
        page,
        2,
        name="Support hours",
        category_label="Professional services",
        status_label="In review",
        priority_value="medium",
    )

    shp.click(
        "#btnApplyChanges",
        element_key="cascade_apply_changes",
        description="Apply changes button on cascade line-item grid",
    )
    expect(page.locator("#stageStatusMsg")).to_contain_text("Changes staged (2 row(s))")

    shp.click(
        "#btnFinalSubmit",
        element_key="cascade_final_commit",
        description="Commit lines control to finalize the cascade workflow",
        verify=lambda p: expect(p.locator("#completionToast")).to_contain_text(
            "Submitted 2 line item(s)"
        ),
    )

    events = _read_audit_events(test_settings.artifacts_dir / "logs" / "healing_audit.jsonl")
    outcomes = [
        e
        for e in events
        if e.get("event_type") == "healing_outcome" and e.get("healing_succeeded") is True
    ]
    methods = {e.get("healing_method") for e in outcomes}
    assert len(outcomes) >= 5, "Expected multiple healed steps across the cascade flow"
    assert methods & {"heuristic", "fuzzy", "llm"}, (
        f"Expected mix of heal strategies, got: {methods}"
    )
