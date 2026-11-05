from __future__ import annotations

from framework.llm.base_provider import LLMProvider
from framework.models.domain import ElementIntent, FailureContext, LocatorCandidate


class UnavailableLLMProvider(LLMProvider):
    """No-op provider when OpenAI mode is set but credentials are missing."""

    def __init__(self, reason: str = "OpenAI API key not configured") -> None:
        self._reason = reason

    @property
    def unavailable_reason(self) -> str:
        return self._reason

    def is_available(self) -> bool:
        return False

    def discover_locator(
        self, intent: ElementIntent, context: FailureContext
    ) -> LocatorCandidate | None:
        return None
