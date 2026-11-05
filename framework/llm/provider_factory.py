from __future__ import annotations

from framework.config.settings import Settings
from framework.llm.base_provider import LLMProvider
from framework.llm.mock_provider import MockLLMProvider
from framework.llm.openai_provider import OpenAIProvider
from framework.llm.prompt_config import LlmPromptOverride
from framework.llm.unavailable_provider import UnavailableLLMProvider


def create_llm_provider(
    settings: Settings, prompt_override: LlmPromptOverride | None = None
) -> LLMProvider:
    if settings.llm_mode == "openai":
        if settings.openai_api_key.strip():
            return OpenAIProvider(settings, prompt_override=prompt_override)
        return UnavailableLLMProvider(
            "LLM_MODE=openai but OPENAI_API_KEY is missing; LLM step will be skipped"
        )
    return MockLLMProvider()


def is_llm_usable(settings: Settings) -> bool:
    return settings.llm_mode == "openai" and bool(settings.openai_api_key.strip())
