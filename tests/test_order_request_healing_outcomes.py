from __future__ import annotations

import json
from pathlib import Path

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, expect


def _audit_events(artifacts_dir: Path) -> list[dict]:
    log = artifacts_dir / "logs" / "healing_audit.jsonl"
    if not log.is_file():
        return []
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_order_request_happy_path(self_healing_page, html_dir: Path) -> None:
    uri = (html_dir / "order_request.html").resolve().as_uri()
    page = self_healing_page.page
    page.goto(uri)

    self_healing_page.fill(
        "#companyName",
        element_key="order_company",
        description="Company name field on license request form",
        value="Acme Corp",
    )
    self_healing_page.select_option(
        "#licenseTier",
        element_key="order_tier",
        description="License tier dropdown on license request form",
        value="business",
    )
    self_healing_page.click(
        "#submitOrder",
        element_key="order_submit",
        description="Submit request button on license request form",
        verify=lambda p: expect(p.locator("#orderSuccessMessage")).to_contain_text("REQ-1001"),
    )


def test_order_request_portal_redesign_is_unrecoverable(
    self_healing_page, test_settings, html_dir: Path
) -> None:
    """Major product change: submit action removed; heuristics and LLM cannot complete the flow."""
    uri = (html_dir / "order_request_portal_redesign.html").resolve().as_uri()
    page = self_healing_page.page
    page.goto(uri)

    with pytest.raises(PlaywrightTimeoutError, match="order_submit"):
        self_healing_page.click(
            "#submitOrder",
            element_key="order_submit",
            description="Submit request button on license request form",
            verify=lambda p: expect(p.locator("#orderSuccessMessage")).to_contain_text("REQ-"),
        )

    events = _audit_events(test_settings.artifacts_dir)
    outcomes = [e for e in events if e.get("event_type") == "healing_outcome" and e.get("element_key") == "order_submit"]
    assert outcomes, "expected healing_outcome audit record"
    final = outcomes[-1]
    assert final.get("healing_succeeded") is False
    assert final.get("healing_status") == "failed"
    assert final.get("healing_method") == "none"

    assert any(e.get("event_type") == "llm_invoked" for e in events)
    assert any(e.get("event_type") == "llm_no_proposal" for e in events)
