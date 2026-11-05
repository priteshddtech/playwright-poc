from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from framework.config.settings import Settings
from framework.models.domain import ExecutionContext
from framework.wrapper.self_healing_page import SelfHealingPage


@pytest.fixture(scope="session")
def html_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "htmls"


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    artifacts = tmp_path / "artifacts"
    return Settings(
        artifacts_dir=artifacts,
        sqlite_path=artifacts / "locator_kb.db",
        llm_mode="mock",
        action_timeout_ms=8000,
    )


@pytest.fixture
def execution_context() -> ExecutionContext:
    return ExecutionContext(
        execution_id=uuid.uuid4().hex,
        test_name="playwright_test",
        application_id="employee_portal",
        environment="test",
    )


@pytest.fixture
def self_healing_page(page, test_settings, execution_context) -> SelfHealingPage:
    return SelfHealingPage(page, execution_context, settings=test_settings)
