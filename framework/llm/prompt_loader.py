from __future__ import annotations

from pathlib import Path

from framework.config.settings import Settings
from framework.llm.prompt_builder import PromptBuilder
from framework.llm.prompt_config import LlmPromptOverride


def _read_optional_file(path: Path | None) -> str:
    if not path:
        return ""
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8").strip()


def resolve_system_prompt(
    settings: Settings, override: LlmPromptOverride | None = None
) -> str:
    """Code override > file > inline env text > framework default."""
    if override and override.system_prompt and override.system_prompt.strip():
        return _apply_placeholders(override.system_prompt.strip(), settings)
    from_file = _read_optional_file(settings.llm_system_prompt_file)
    if from_file:
        return _apply_placeholders(from_file, settings)
    if settings.llm_system_prompt.strip():
        return _apply_placeholders(settings.llm_system_prompt.strip(), settings)
    return PromptBuilder.DEFAULT_SYSTEM_PROMPT


def resolve_user_context(
    settings: Settings, override: LlmPromptOverride | None = None
) -> str:
    if override and override.user_context and override.user_context.strip():
        return _apply_placeholders(override.user_context.strip(), settings)
    from_file = _read_optional_file(settings.llm_user_context_file)
    if from_file:
        return _apply_placeholders(from_file, settings)
    if settings.llm_user_context.strip():
        return _apply_placeholders(settings.llm_user_context.strip(), settings)
    return ""


def _apply_placeholders(text: str, settings: Settings) -> str:
    return (
        text.replace("{application_id}", settings.application_id)
        .replace("{environment}", settings.environment)
    )


def create_prompt_builder(
    settings: Settings, override: LlmPromptOverride | None = None
) -> PromptBuilder:
    return PromptBuilder(
        system_prompt=resolve_system_prompt(settings, override),
        user_context=resolve_user_context(settings, override),
    )
