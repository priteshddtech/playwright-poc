from __future__ import annotations

from abc import ABC, abstractmethod

from framework.models.domain import ElementIntent, FailureContext, LocatorCandidate


class LLMProvider(ABC):
    def is_available(self) -> bool:
        """True when this provider can call the LLM API (credentials configured)."""
        return True

    @abstractmethod
    def discover_locator(
        self, intent: ElementIntent, context: FailureContext
    ) -> LocatorCandidate | None:
        ...
