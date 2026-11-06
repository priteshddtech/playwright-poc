"""
Open the employee registration HTML form in a visible Playwright browser
and run the automation flow (optionally with self-healing on changed HTML).

Usage:
    python run_visible_demo.py
    python run_visible_demo.py --form changed --self-heal
    python run_visible_demo.py --form iframe --self-heal
    python run_visible_demo.py --form cascade --wait-for-enter
    python run_visible_demo.py --form cascade-changed --self-heal --wait-for-enter
"""

from __future__ import annotations

import argparse
import sys
import time
import uuid
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright

from framework.config.settings import get_settings
from framework.models.domain import ExecutionContext, LocatorDefinition, LocatorStrategy
from framework.wrapper.self_healing_page import SelfHealingPage

PROJECT_ROOT = Path(__file__).resolve().parent
HTML_DIR = PROJECT_ROOT / "htmls"

SUCCESS_TEXT = "Employee registered successfully!"
DEFAULT_HOLD_SECONDS = 2


def _success_locator(form: str) -> str:
    return "#successMessage" if form == "original" else "#successBanner"


def _wait_for_success_visible(page, form: str) -> None:
    if form in ("cascade", "cascade-changed"):
        banner = page.locator(
            "#successBanner" if form == "cascade" else "#completionToast"
        )
        expect(banner).to_be_visible(timeout=15_000)
        expect(banner).to_contain_text("Submitted 2 line item(s)")
        return
    locator = page.locator(_success_locator(form))
    expect(locator).to_be_visible(timeout=15_000)
    expect(locator).to_have_text(SUCCESS_TEXT)


def _fill_cascade_line_row(
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


def _fill_cascade_line_items(page: Page) -> None:
    page.locator("#cascadeRegion").select_option(value="americas")
    page.locator("#cascadeDepartment").select_option(value="sales")
    page.locator("#cascadeTeam").select_option(label="Field sales")
    page.locator("#btnRevealTable").click()
    expect(page.locator("#lineItemsPanel")).to_be_visible()

    _fill_cascade_line_row(
        page,
        1,
        name="Laptop bundle",
        category_label="Hardware",
        status_label="Draft",
        priority_value="high",
    )
    page.locator("#btnAddRow").click()
    _fill_cascade_line_row(
        page,
        2,
        name="Support hours",
        category_label="Professional services",
        status_label="In review",
        priority_value="medium",
    )
    page.locator("#btnApplyChanges").click()
    expect(page.locator("#applyStatus")).to_contain_text("Changes staged (2 row(s))")
    page.locator("#btnFinalSubmit").click()


def _fill_cascade_line_items_self_heal(shp: SelfHealingPage) -> None:
    page = shp.page
    shp.select_option(
        "#cascadeRegion",
        element_key="demo_cascade_region",
        description="Region dropdown on line-item cascade configuration form",
        value="americas",
    )
    shp.select_option(
        "#cascadeDepartment",
        element_key="demo_cascade_department",
        description="Department dropdown on line-item cascade configuration form",
        value="sales",
    )
    shp.select_option(
        "#cascadeTeam",
        element_key="demo_cascade_team",
        description="Team dropdown on line-item cascade configuration form",
        value="field-sales",
    )
    shp.click(
        "#btnRevealTable",
        element_key="demo_cascade_build_grid",
        description="Build line-item grid button on cascade configuration form",
    )
    expect(page.locator("#lineItemsPanel")).to_be_visible()

    _fill_cascade_line_row(
        page,
        1,
        name="Laptop bundle",
        category_label="Hardware",
        status_label="Draft",
        priority_value="high",
    )
    shp.click(
        "#btnAddRow",
        element_key="demo_cascade_add_row",
        description="Add row button on cascade line-item grid",
    )
    _fill_cascade_line_row(
        page,
        2,
        name="Support hours",
        category_label="Professional services",
        status_label="In review",
        priority_value="medium",
    )
    shp.click(
        "#btnApplyChanges",
        element_key="demo_cascade_apply",
        description="Apply changes button on cascade line-item grid",
    )
    expect(page.locator("#stageStatusMsg")).to_contain_text("Changes staged (2 row(s))")
    shp.click(
        "#btnFinalSubmit",
        element_key="demo_cascade_submit",
        description="Commit lines control to finalize the cascade workflow",
        verify=lambda p: expect(p.locator("#completionToast")).to_contain_text(
            "Submitted 2 line item(s)"
        ),
    )


def _fill_original_form(shp: SelfHealingPage) -> None:
    shp.fill(
        "#fullName",
        element_key="employee_full_name",
        description="Full name input on employee registration form",
        value="Jane Doe",
    )
    shp.fill(
        "#email",
        element_key="employee_email",
        description="Email input on employee registration form",
        value="jane@example.com",
    )
    shp.select_option(
        "#department",
        element_key="employee_department",
        description="Department dropdown on employee registration form",
        value="IT",
    )
    shp.page.locator("#permanent").check()
    shp.page.locator("#terms").check()
    shp.click(
        "#submitButton",
        element_key="employee_form_submit",
        description="Submit button for employee registration form",
        verify=lambda p: expect(p.locator("#successMessage")).to_have_text(
            "Employee registered successfully!"
        ),
    )


def _fill_iframe_form(shp: SelfHealingPage, self_heal: bool) -> None:
    page = shp.page
    page.locator("#actionsFrame").wait_for(state="attached")
    page.frame(name="actionsFrame").wait_for_selector("#iframeRegisterBtn")

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

    if self_heal:
        submit_locator: str | LocatorDefinition = "#submitButton"
    else:
        submit_locator = LocatorDefinition(
            strategy=LocatorStrategy.CSS,
            value="#iframeRegisterBtn",
            frame_name="actionsFrame",
        )
    shp.click(
        submit_locator,
        element_key="iframe_employee_form_submit",
        description="Complete registration action in the embedded actions panel",
        verify=lambda p: expect(p.locator("#successBanner")).to_have_text(
            "Employee registered successfully!"
        ),
    )


def _fill_changed_form(shp: SelfHealingPage, self_heal: bool) -> None:
    shp.fill(
        "#empFullName",
        element_key="employee_full_name_v2",
        description="Full name input on employee registration form",
        value="John Smith",
    )
    shp.fill(
        "#empEmail",
        element_key="employee_email_v2",
        description="Email input on employee registration form",
        value="john@example.com",
    )
    shp.select_option(
        "#empDepartment",
        element_key="employee_department_v2",
        description="Department dropdown on employee registration form",
        value="HR",
    )
    shp.page.locator("#empPermanent").check()
    shp.page.locator("#empTerms").check()

    submit_locator = "#submitButton" if self_heal else "#registerEmployeeBtn"
    shp.click(
        submit_locator,
        element_key="employee_form_submit",
        description="Submit button for employee registration form",
        verify=lambda p: expect(p.locator("#successBanner")).to_have_text(
            "Employee registered successfully!"
        ),
    )


def run_demo(
    form: str,
    self_heal: bool,
    slow_mo_ms: int,
    hold_seconds: int,
    wait_for_enter: bool,
) -> None:
    settings = get_settings()
    updates: dict = {}
    if form == "iframe":
        updates["action_timeout_ms"] = 12_000
    updates["log_healing_summary_console"] = True
    if updates:
        settings = settings.model_copy(update=updates)

    html_files = {
        "original": "form1.html",
        "changed": "form1_changed.html",
        "iframe": "form1_iframe_host.html",
        "llm-icon": "form1_llm_icon_confirm.html",
        "llm-link": "form1_llm_link_continue.html",
        "llm-decoy": "form1_llm_decoy_grid.html",
        "cascade": "form_cascade_line_items.html",
        "cascade-changed": "form_cascade_line_items_changed.html",
    }
    html_file = html_files[form]
    form_uri = (HTML_DIR / html_file).resolve().as_uri()

    execution = ExecutionContext(
        execution_id=uuid.uuid4().hex,
        test_name="visible_demo",
        application_id=settings.application_id,
        environment=settings.environment,
    )

    print(f"Opening {html_file} in Chromium (visible browser)...")
    if self_heal and form in ("changed", "iframe", "llm-icon", "llm-link", "llm-decoy"):
        print("Using stale locator #submitButton — watch self-healing recover.")
    if form in ("llm-icon", "llm-link", "llm-decoy"):
        print("Submit control is obfuscated — heuristics should fail and LLM should run.")
    if form == "iframe":
        print("Submit control is inside iframe 'actionsFrame' (LLM/heuristics + frame metadata).")
    if form == "cascade":
        print(
            "Cascade: region → department → team → line-item grid (+ row) → apply → submit."
        )
    if form == "cascade-changed" and self_heal:
        print(
            "Using stale v1 locators on changed cascade markup — heuristics/fuzzy/LLM will recover."
        )
    elif form == "cascade-changed":
        print("Changed cascade form — pass --self-heal to demo stale locator recovery.")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False, slow_mo=slow_mo_ms)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()
        shp = SelfHealingPage(page, execution, settings=settings)

        page.goto(form_uri)
        time.sleep(0.5)

        if form == "iframe":
            _fill_iframe_form(shp, self_heal=self_heal)
        elif form == "changed":
            _fill_changed_form(shp, self_heal=self_heal)
        elif form in ("llm-icon", "llm-link", "llm-decoy"):
            _fill_changed_form(shp, self_heal=True)
        elif form == "cascade":
            _fill_cascade_line_items(page)
        elif form == "cascade-changed":
            if self_heal:
                _fill_cascade_line_items_self_heal(shp)
            else:
                page.locator("#cfgRegionZone").select_option(value="americas")
                page.locator("#cfgDeptUnit").select_option(value="sales")
                page.locator("#cascadeTeamPod").select_option(label="Field sales")
                page.locator("#btnLoadLineGrid").click()
                _fill_cascade_line_row(
                    page,
                    1,
                    name="Laptop bundle",
                    category_label="Hardware",
                    status_label="Draft",
                    priority_value="high",
                )
                page.locator("#btnInsertLine").click()
                _fill_cascade_line_row(
                    page,
                    2,
                    name="Support hours",
                    category_label="Professional services",
                    status_label="In review",
                    priority_value="medium",
                )
                page.locator("#btnStageLineChanges").click()
                page.locator("#btnCommitLines").click()
        else:
            _fill_original_form(shp)

        _wait_for_success_visible(page, form)
        print("Success message is visible on the page.")
        if wait_for_enter:
            input("Press Enter to close the browser...")
        else:
            print(f"Closing browser in {hold_seconds} second(s)...")
            time.sleep(hold_seconds)

        context.close()
        browser.close()
        print("Browser closed.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run employee form automation in a visible Playwright browser."
    )
    parser.add_argument(
        "--form",
        choices=(
            "original",
            "changed",
            "iframe",
            "llm-icon",
            "llm-link",
            "llm-decoy",
            "cascade",
            "cascade-changed",
        ),
        default="original",
        help="original | changed | iframe | llm-* | cascade | cascade-changed",
    )
    parser.add_argument(
        "--self-heal",
        action="store_true",
        help="Use stale locators so healing runs (changed/iframe/cascade-changed)",
    )
    parser.add_argument(
        "--slow-mo",
        type=int,
        default=400,
        metavar="MS",
        help="Delay between actions in milliseconds (default: 400)",
    )
    parser.add_argument(
        "--hold",
        type=int,
        default=DEFAULT_HOLD_SECONDS,
        metavar="SECONDS",
        help=f"Seconds to keep browser open after success before auto-close (default: {DEFAULT_HOLD_SECONDS})",
    )
    parser.add_argument(
        "--wait-for-enter",
        action="store_true",
        help="Keep browser open until you press Enter (instead of auto-close)",
    )
    args = parser.parse_args(argv)

    if args.self_heal and args.form not in ("changed", "iframe", "cascade-changed"):
        print(
            "--self-heal only applies with --form changed, iframe, or cascade-changed",
            file=sys.stderr,
        )
        return 1

    try:
        run_demo(
            form=args.form,
            self_heal=args.self_heal,
            slow_mo_ms=args.slow_mo,
            hold_seconds=args.hold,
            wait_for_enter=args.wait_for_enter,
        )
    except KeyboardInterrupt:
        print("\nStopped.")
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
