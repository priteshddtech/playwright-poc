from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import expect


@pytest.fixture
def iframe_settings(test_settings):
    """Isolated DB and mock LLM; heuristics unlikely to match iframe-only control text."""
    test_settings.llm_mode = "mock"
    return test_settings


def test_self_heal_submit_button_inside_iframe(
    page, iframe_settings, execution_context, html_dir: Path
) -> None:
    from framework.wrapper.self_healing_page import SelfHealingPage

    host = (html_dir / "form1_iframe_host.html").resolve().as_uri()
    page.goto(host)
    page.locator("#actionsFrame").wait_for(state="attached")
    page.frame(name="actionsFrame").wait_for_selector("#iframeRegisterBtn")

    shp = SelfHealingPage(page, execution_context, settings=iframe_settings)

    shp.fill(
        "#empFullName",
        element_key="iframe_employee_full_name",
        description="Full name field on iframe host registration form",
        value="Alex Kim",
    )
    shp.fill(
        "#empEmail",
        element_key="iframe_employee_email",
        description="Email field on iframe host registration form",
        value="alex@example.com",
    )
    shp.select_option(
        "#empDepartment",
        element_key="iframe_employee_department",
        description="Department field on iframe host registration form",
        value="Finance",
    )
    page.locator("#empPermanent").check()
    page.locator("#empTerms").check()

    shp.click(
        "#submitButton",
        element_key="iframe_employee_form_submit",
        description="Complete registration action in the embedded actions panel",
        verify=lambda p: expect(p.locator("#successBanner")).to_have_text(
            "Employee registered successfully!"
        ),
    )
