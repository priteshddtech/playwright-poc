from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import expect


@pytest.fixture
def fuzzy_settings(test_settings):
    test_settings.llm_mode = "mock"
    test_settings.fuzzy_match_enabled = True
    test_settings.fuzzy_match_threshold = 0.85
    return test_settings


def test_fuzzy_heal_renamed_field_ids(
    page, fuzzy_settings, execution_context, html_dir: Path
) -> None:
    from framework.wrapper.self_healing_page import SelfHealingPage

    form_uri = (html_dir / "form1_fuzzy_rename.html").resolve().as_uri()
    page.goto(form_uri)
    shp = SelfHealingPage(page, execution_context, settings=fuzzy_settings)

    shp.fill(
        "#fullName",
        element_key="fuzzy_full_name",
        description="Full name input on employee registration form",
        value="Taylor Lee",
    )
    shp.fill(
        "#email",
        element_key="fuzzy_email",
        description="Email input on employee registration form",
        value="taylor@example.com",
    )
    shp.select_option(
        "#department",
        element_key="fuzzy_department",
        description="Department dropdown on employee registration form",
        value="Finance",
    )
    page.locator("#employment_permanent").check()
    page.locator("#terms_accepted").check()

    shp.click(
        "#submitButton",
        element_key="fuzzy_form_submit",
        description="Submit button for employee registration form",
        verify=lambda p: expect(p.locator("#successMessage")).to_have_text(
            "Employee registered successfully!"
        ),
    )
