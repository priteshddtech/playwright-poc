from __future__ import annotations

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


def test_cascade_dropdowns_line_items_grid_submit(
    page: Page, html_dir: Path
) -> None:
    """Cascading dropdowns reveal a dynamic table; apply + submit completes the flow."""
    form_uri = (html_dir / "form_cascade_line_items.html").resolve().as_uri()
    page.goto(form_uri)

    expect(page.locator("#cascadeDepartment")).not_to_be_visible()
    page.locator("#cascadeRegion").select_option(value="americas")
    expect(page.locator("#cascadeDepartment")).to_be_visible()
    expect(page.locator("#cascadeTeam")).not_to_be_visible()

    page.locator("#cascadeDepartment").select_option(value="sales")
    expect(page.locator("#cascadeTeam")).to_be_visible()
    expect(page.locator("#btnRevealTable")).to_be_disabled()

    page.locator("#cascadeTeam").select_option(label="Field sales")
    expect(page.locator("#btnRevealTable")).to_be_enabled()

    page.locator("#btnRevealTable").click()
    expect(page.locator("#lineItemsPanel")).to_be_visible()
    expect(page.locator("#tableContextTitle")).to_contain_text("Americas / Sales / Field sales")
    expect(page.locator("#lineItemsBody tr.line-item-row")).to_have_count(1)

    _fill_line_row(
        page,
        1,
        name="Laptop bundle",
        category_label="Hardware",
        status_label="Draft",
        priority_value="high",
    )

    page.locator("#btnAddRow").click()
    expect(page.locator("#lineItemsBody tr.line-item-row")).to_have_count(2)

    _fill_line_row(
        page,
        2,
        name="Support hours",
        category_label="Professional services",
        status_label="In review",
        priority_value="medium",
    )

    expect(page.locator("#btnFinalSubmit")).to_be_disabled()
    page.locator("#btnApplyChanges").click()
    expect(page.locator("#applyStatus")).to_contain_text("Changes staged (2 row(s))")
    expect(page.locator("#btnFinalSubmit")).to_be_enabled()

    page.locator("#btnFinalSubmit").click()
    expect(page.locator("#successBanner")).to_be_visible()
    expect(page.locator("#successBanner")).to_have_text(
        "Submitted 2 line item(s) for Field sales."
    )


def test_cascade_region_changes_category_options(page: Page, html_dir: Path) -> None:
    form_uri = (html_dir / "form_cascade_line_items.html").resolve().as_uri()
    page.goto(form_uri)

    page.locator("#cascadeRegion").select_option(value="emea")
    page.locator("#cascadeDepartment").select_option(value="finance")
    page.locator("#cascadeTeam").select_option(label="Payroll")
    page.locator("#btnRevealTable").click()

    category = page.locator("#lineItemsBody tr[data-row-index='1'] .item-category")
    expect(category.locator("option")).to_contain_text(["Consulting", "Regulatory fee"])
