from __future__ import annotations

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from framework.models.domain import ElementIntent, LocatorDefinition
from framework.utils.locator_resolver import LocatorResolver


class RetryManager:
    """Execute actions and optional smart timing retries."""

    def __init__(self, timeout_ms: int) -> None:
        self._timeout_ms = timeout_ms

    def execute(self, page: Page, intent: ElementIntent, definition: LocatorDefinition) -> None:
        locator = LocatorResolver.resolve(page, definition)
        locator.wait_for(state="visible", timeout=self._timeout_ms)
        self._perform_action(locator, intent)

    def smart_wait_retry(self, page: Page, intent: ElementIntent) -> bool:
        definition = intent.primary_locator
        locator = LocatorResolver.resolve(page, definition)
        try:
            locator.wait_for(state="attached", timeout=self._timeout_ms * 2)
            locator.wait_for(state="visible", timeout=self._timeout_ms * 2)
            self._perform_action(locator, intent)
            return True
        except PlaywrightTimeoutError:
            return False

    @staticmethod
    def _perform_action(locator, intent: ElementIntent) -> None:
        from framework.models.domain import ActionType

        if intent.action == ActionType.CLICK:
            locator.click()
        elif intent.action == ActionType.FILL:
            locator.fill(intent.action_value or "")
        elif intent.action == ActionType.SELECT_OPTION:
            locator.select_option(intent.action_value or "")
        elif intent.action == ActionType.CHECK:
            locator.check()
        elif intent.action == ActionType.UNCHECK:
            locator.uncheck()
        elif intent.action == ActionType.PRESS:
            locator.press(intent.action_value or "Enter")
