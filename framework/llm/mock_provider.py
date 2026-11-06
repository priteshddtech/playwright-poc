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

        if "btncommitlines" in html and ("commit" in desc or "finalize" in desc or "cascade" in desc):
            return LocatorCandidate(
                definition=LocatorDefinition(
                    strategy=LocatorStrategy.CSS,
                    value="#btnCommitLines",
                ),
                method=HealingMethod.LLM,
                llm_confidence=97.0,
                reason="Mock: cascade form final commit button (renamed from Submit)",
            )

        if "submit" in desc or "registration" in desc:
            if "vault_action_confirm" in html:
                return LocatorCandidate(
                    definition=LocatorDefinition(
                        strategy=LocatorStrategy.CSS,
                        value="#vault_action_confirm",
                    ),
                    method=HealingMethod.LLM,
                    llm_confidence=97.0,
                    reason="Mock: icon-only confirm control (no Submit heuristics)",
                )
            if "regflowprimary" in html:
                return LocatorCandidate(
                    definition=LocatorDefinition(
                        strategy=LocatorStrategy.CSS,
                        value="#regFlowPrimary",
                    ),
                    method=HealingMethod.LLM,
                    llm_confidence=96.5,
                    reason="Mock: continue link styled as primary action",
                )
            if "host_xk31" in html:
                return LocatorCandidate(
                    definition=LocatorDefinition(
                        strategy=LocatorStrategy.CSS,
                        value="#host_xk31",
                    ),
                    method=HealingMethod.LLM,
                    llm_confidence=96.0,
                    reason="Mock: primary chip among decoy toolbar controls",
                )
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
