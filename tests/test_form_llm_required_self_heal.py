from __future__ import annotations

import json
from pathlib import Path

import pytest
from playwright.sync_api import expect


@pytest.fixture
def llm_required_settings(test_settings):
    test_settings.llm_mode = "mock"
    test_settings.fuzzy_match_enabled = True
    return test_settings


def _fill_common_fields(page, shp) -> None:
    shp.fill(
        "#empFullName",
        element_key="llm_full_name",
        description="Full name input on employee registration form",
        value="Jordan Lee",
    )
    shp.fill(
        "#empEmail",
        element_key="llm_email",
        description="Email input on employee registration form",
        value="jordan@example.com",
    )
    shp.select_option(
        "#empDepartment",
        element_key="llm_department",
        description="Department dropdown on employee registration form",
        value="IT",
    )
    page.locator("#empPermanent").check()
    page.locator("#empTerms").check()


def _assert_llm_healed(audit_log: Path, element_key: str) -> None:
    assert audit_log.is_file(), "expected healing audit log"
    events = [json.loads(line) for line in audit_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    invoked = [
        e
        for e in events
        if e.get("event_type") == "llm_invoked" and e.get("element_key") == element_key
    ]
    assert invoked, f"LLM was not invoked for {element_key}"

    outcomes = [
        e
        for e in events
        if e.get("event_type") == "healing_outcome"
        and e.get("element_key") == element_key
        and e.get("healing_succeeded") is True
    ]
    assert outcomes, f"expected successful healing outcome for {element_key}"
    assert outcomes[-1].get("solved_by_llm") is True
    assert outcomes[-1].get("healing_method") == "llm"


@pytest.mark.parametrize(
    ("html_file", "element_key"),
    [
        ("form1_llm_icon_confirm.html", "llm_icon_submit"),
        ("form1_llm_link_continue.html", "llm_link_submit"),
        ("form1_llm_decoy_grid.html", "llm_decoy_submit"),
    ],
)
def test_self_heal_requires_llm_for_obfuscated_submit(
    page,
    llm_required_settings,
    execution_context,
    html_dir: Path,
    html_file: str,
    element_key: str,
) -> None:
    from framework.wrapper.self_healing_page import SelfHealingPage

    form_uri = (html_dir / html_file).resolve().as_uri()
    page.goto(form_uri)
    shp = SelfHealingPage(page, execution_context, settings=llm_required_settings)
    _fill_common_fields(page, shp)

    shp.click(
        "#submitButton",
        element_key=element_key,
        description="Submit button for employee registration form",
        verify=lambda p: expect(p.locator("#successBanner")).to_have_text(
            "Employee registered successfully!"
        ),
    )

    audit_log = llm_required_settings.artifacts_dir / "logs" / "healing_audit.jsonl"
    _assert_llm_healed(audit_log, element_key)
