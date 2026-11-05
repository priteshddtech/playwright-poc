from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LlmPromptOverride:
    """Code-level LLM prompt overrides (highest priority when fields are set)."""

    system_prompt: str | None = None
    user_context: str | None = None
