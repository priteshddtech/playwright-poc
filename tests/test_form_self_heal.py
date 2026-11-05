from __future__ import annotations

from pathlib import Path

from playwright.sync_api import expect


def test_self_heal_stale_submit_locator(
    self_healing_page, html_dir: Path
) -> None:
    """Uses changed HTML with stale locators; healing should recover submit action."""
    form_path = (html_dir / "form1_changed.html").resolve().as_uri()
    page = self_healing_page.page
    page.goto(form_path)

    self_healing_page.fill(
        "#empFullName",
        element_key="employee_full_name_v2",
        description="Full name input on employee registration form",
        value="John Smith",
    )
    self_healing_page.fill(
        "#empEmail",
        element_key="employee_email_v2",
        description="Email input on employee registration form",
        value="john@example.com",
    )
    self_healing_page.select_option(
        "#empDepartment",
        element_key="employee_department_v2",
        description="Department dropdown on employee registration form",
        value="HR",
    )
    page.locator("#empPermanent").check()
    page.locator("#empTerms").check()

    self_healing_page.click(
        "#submitButton",
        element_key="employee_form_submit",
        description="Submit button for employee registration form",
        verify=lambda p: expect(p.locator("#successBanner")).to_have_text(
            "Employee registered successfully!"
        ),
    )
