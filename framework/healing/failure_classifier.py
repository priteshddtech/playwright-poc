from __future__ import annotations

from playwright.sync_api import Page

from framework.models.domain import ElementIntent, FailureCategory, FailureContext
from framework.utils.locator_resolver import LocatorResolver


class FailureClassifier:
    def classify(self, context: FailureContext) -> FailureCategory:
        msg = context.error_message.lower()
        if "waiting for locator" in msg:
            return FailureCategory.LOCATOR_MISSING
        if any(k in msg for k in ("timeout", "waiting", "not visible", "not enabled")):
            return FailureCategory.TIMING
        if "iframe" in msg or len(context.frames) > 1:
            return FailureCategory.IFRAME_CHANGED
        if "strict mode violation" in msg or "locator" in msg:
            return FailureCategory.LOCATOR_CHANGED
        if not self._has_interactive_elements(context.html_pruned):
            return FailureCategory.BUSINESS_LOGIC
        return FailureCategory.UI_CHANGED

    def refine_with_page(
        self, page: Page, intent: ElementIntent, category: FailureCategory
    ) -> FailureCategory:
        """Use live DOM to distinguish missing vs changed locators."""
        try:
            locator = LocatorResolver.resolve(page, intent.primary_locator)
            count = locator.count()
        except Exception:
            return FailureCategory.LOCATOR_MISSING

        if count == 0:
            return FailureCategory.LOCATOR_MISSING
        if count > 1:
            return FailureCategory.LOCATOR_CHANGED
        if category == FailureCategory.LOCATOR_MISSING:
            try:
                if not locator.first.is_visible():
                    return FailureCategory.TIMING
            except Exception:
                return FailureCategory.TIMING
            return FailureCategory.LOCATOR_CHANGED
        return category

    @staticmethod
    def _has_interactive_elements(html: str) -> bool:
        lowered = html.lower()
        return any(tag in lowered for tag in ("<button", "<input", "<select", "<textarea"))
