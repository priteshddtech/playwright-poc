from __future__ import annotations

from playwright.sync_api import Frame, Locator, Page

from framework.models.domain import LocatorDefinition, LocatorStrategy


class LocatorResolver:
    """Build Playwright locators from structured definitions."""

    @staticmethod
    def resolve(page: Page, definition: LocatorDefinition) -> Locator:
        frame = LocatorResolver._resolve_frame(page, definition)
        return LocatorResolver._resolve_on_frame(frame, definition)

    @staticmethod
    def _resolve_frame(page: Page, definition: LocatorDefinition) -> Page | Frame:
        if not definition.frame_name and not definition.frame_url:
            return page
        for frame in page.frames:
            if definition.frame_name and frame.name == definition.frame_name:
                return frame
            if definition.frame_url and definition.frame_url in (frame.url or ""):
                return frame
        if definition.frame_name:
            for frame in page.frames:
                if frame.name == definition.frame_name:
                    return frame
        return page

    @staticmethod
    def _resolve_on_frame(frame: Page | Frame, definition: LocatorDefinition) -> Locator:
        if definition.strategy == LocatorStrategy.CSS:
            return frame.locator(definition.value)
        if definition.strategy == LocatorStrategy.ROLE:
            return frame.get_by_role(definition.role or "button", name=definition.name or "")
        if definition.strategy == LocatorStrategy.TEXT:
            return frame.get_by_text(definition.value)
        if definition.strategy == LocatorStrategy.LABEL:
            return frame.get_by_label(definition.value)
        if definition.strategy == LocatorStrategy.PLACEHOLDER:
            return frame.get_by_placeholder(definition.value)
        if definition.strategy == LocatorStrategy.TEST_ID:
            return frame.get_by_test_id(definition.value)
        return frame.locator(definition.value)

    @staticmethod
    def from_css_string(raw: str) -> LocatorDefinition:
        return LocatorDefinition(strategy=LocatorStrategy.CSS, value=raw)
