from __future__ import annotations

from openai import OpenAI

from framework.config.settings import Settings
from framework.llm.base_provider import LLMProvider
from framework.llm.prompt_config import LlmPromptOverride
from framework.llm.prompt_loader import create_prompt_builder
from framework.llm.response_parser import ResponseParser
from framework.models.domain import ElementIntent, FailureContext, LocatorCandidate


class OpenAIProvider(LLMProvider):
    def __init__(
        self,
        settings: Settings,
        prompt_override: LlmPromptOverride | None = None,
    ) -> None:
        self._settings = settings
        self._prompt_override = prompt_override
        self._client: OpenAI | None = None
        self._prompt_builder = create_prompt_builder(settings, prompt_override)
        self._parser = ResponseParser()

    def set_prompt_override(self, override: LlmPromptOverride | None) -> None:
        self._prompt_override = override
        self._prompt_builder = create_prompt_builder(self._settings, override)

    def is_available(self) -> bool:
        return bool(self._settings.openai_api_key.strip())

    def _get_client(self) -> OpenAI | None:
        if not self.is_available():
            return None
        if self._client is None:
            self._client = OpenAI(api_key=self._settings.openai_api_key)
        return self._client

    def discover_locator(
        self, intent: ElementIntent, context: FailureContext
    ) -> LocatorCandidate | None:
        client = self._get_client()
        if client is None:
            return None

        try:
            user_message = self._prompt_builder.build_user_message(intent, context)
            response = client.chat.completions.create(
                model=self._settings.openai_model,
                messages=[
                    {"role": "system", "content": self._prompt_builder.system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.1,
            )
            content = response.choices[0].message.content or ""
            return self._parser.parse(content)
        except Exception:
            return None
