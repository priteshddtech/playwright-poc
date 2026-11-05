from __future__ import annotations

from framework.llm.base_provider import LLMProvider
from framework.models.domain import (
    ElementIntent,
    FailureContext,
    HealingMethod,
    LocatorCandidate,
    LocatorDefinition,
    LocatorStrategy,
)


class MockLLMProvider(LLMProvider):
    """Deterministic LLM stub for CI and offline runs."""

    def discover_locator(
        self, intent: ElementIntent, context: FailureContext
    ) -> LocatorCandidate | None:
        desc = intent.description.lower()
        html = context.html_pruned.lower()

        if "submit" in desc or "registration" in desc:
            if "iframeregisterbtn" in html or "iframe-complete-btn" in html:
                frame_name = "actionsFrame"
                for frame in context.frames:
                    if "iframe_actions" in (frame.url or ""):
                        frame_name = frame.name or frame_name
                        break
                return LocatorCandidate(
                    definition=LocatorDefinition(
                        strategy=LocatorStrategy.CSS,
                        value="#iframeRegisterBtn",
                        frame_name=frame_name,
                    ),
                    method=HealingMethod.LLM,
                    llm_confidence=97.0,
                    reason="Mock: submit button moved into actions iframe",
                )
            if "registeremployeebtn" in html or "btn-register" in html:
                return LocatorCandidate(
                    definition=LocatorDefinition(
                        strategy=LocatorStrategy.CSS,
                        value="#registerEmployeeBtn",
                    ),
                    method=HealingMethod.LLM,
                    llm_confidence=96.0,
                    reason="Mock: mapped stale submit id to changed button id",
                )
            return LocatorCandidate(
                definition=LocatorDefinition(
                    strategy=LocatorStrategy.ROLE,
                    value="role:button:Submit",
                    role="button",
                    name="Submit",
                ),
                method=HealingMethod.LLM,
                llm_confidence=94.0,
                reason="Mock: fallback submit role locator",
            )

        return None
