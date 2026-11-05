from __future__ import annotations

from pathlib import Path

from playwright.sync_api import expect


def test_employee_registration_happy_path(
    self_healing_page, html_dir: Path
) -> None:
    form_path = (html_dir / "form1.html").resolve().as_uri()
    page = self_healing_page.page
    page.goto(form_path)

    self_healing_page.fill(
        "#fullName",
        element_key="employee_full_name",
        description="Full name input on employee registration form",
        value="Jane Doe",
    )
    self_healing_page.fill(
        "#email",
        element_key="employee_email",
        description="Email input on employee registration form",
        value="jane@example.com",
    )
    self_healing_page.select_option(
        "#department",
        element_key="employee_department",
        description="Department dropdown on employee registration form",
        value="IT",
    )
    self_healing_page.page.locator("#permanent").check()
    self_healing_page.page.locator("#terms").check()

    self_healing_page.click(
        "#submitButton",
        element_key="employee_form_submit",
        description="Submit button for employee registration form",
        verify=lambda p: expect(p.locator("#successMessage")).to_have_text(
            "Employee registered successfully!"
        ),
    )
