from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from framework.models.domain import HealingEventRecord, LocatorDefinition


class LocatorRepository(ABC):
    @abstractmethod
    def get_current(
        self, application_id: str, page_key: str, element_key: str
    ) -> Optional[LocatorDefinition]:
        ...

    @abstractmethod
    def get_history(
        self, application_id: str, page_key: str, element_key: str
    ) -> list[str]:
        ...

    @abstractmethod
    def promote_locator(
        self,
        application_id: str,
        page_key: str,
        element_key: str,
        locator: LocatorDefinition,
        confidence: float,
    ) -> None:
        ...

    @abstractmethod
    def append_history(
        self,
        application_id: str,
        page_key: str,
        element_key: str,
        locator: str,
        success: bool,
    ) -> None:
        ...

    @abstractmethod
    def record_healing_event(self, event: HealingEventRecord) -> None:
        ...
