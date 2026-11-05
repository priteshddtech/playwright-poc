from pathlib import Path

from framework.config.settings import Settings
from framework.llm.prompt_builder import PromptBuilder
from framework.llm.prompt_config import LlmPromptOverride
from framework.llm.prompt_loader import create_prompt_builder, resolve_system_prompt


def test_default_system_prompt_when_no_override() -> None:
    settings = Settings()
    assert resolve_system_prompt(settings) == PromptBuilder.DEFAULT_SYSTEM_PROMPT


def test_system_prompt_from_file(tmp_path: Path) -> None:
    prompt_file = tmp_path / "custom.prompt"
    prompt_file.write_text("Custom prompt for {application_id}", encoding="utf-8")
    settings = Settings(
        application_id="my_app",
        llm_system_prompt_file=prompt_file,
    )
    assert resolve_system_prompt(settings) == "Custom prompt for my_app"


def test_code_override_beats_env_file(tmp_path: Path) -> None:
    prompt_file = tmp_path / "file.prompt"
    prompt_file.write_text("From file", encoding="utf-8")
    settings = Settings(
        llm_system_prompt="From env",
        llm_system_prompt_file=prompt_file,
    )
    override = LlmPromptOverride(system_prompt="From code")
    assert resolve_system_prompt(settings, override) == "From code"


def test_user_context_in_payload() -> None:
    settings = Settings(llm_user_context="ERP checkout module")
    builder = create_prompt_builder(settings)
    from framework.models.domain import ActionType, ElementIntent, FailureContext, FrameInfo

    intent = ElementIntent("k", "desc", "#x", ActionType.CLICK)
    ctx = FailureContext(
        url="http://x",
        title="t",
        html_pruned="<div/>",
        html_snapshot_path=None,
        screenshot_path=None,
        accessibility_tree={},
        frames=[FrameInfo("", "", 0)],
        console_logs=[],
        failed_locator="#x",
        error_message="err",
    )
    message = builder.build_user_message(intent, ctx)
    assert "application_context" in message
    assert "ERP checkout module" in message
