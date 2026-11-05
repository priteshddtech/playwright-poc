from __future__ import annotations

import re

from playwright.sync_api import Frame, Page

from framework.healing.fuzzy_matcher import FuzzyMatcher
from framework.models.domain import ElementIntent, HealingMethod, LocatorCandidate, LocatorDefinition, LocatorStrategy


class HeuristicEngine:
    """Deterministic locator discovery using Playwright semantic APIs."""

    def __init__(self, fuzzy_matcher: FuzzyMatcher | None = None) -> None:
        self._fuzzy_matcher = fuzzy_matcher

    def discover(self, page: Page, intent: ElementIntent) -> list[LocatorCandidate]:
        candidates: list[LocatorCandidate] = []
        if self._fuzzy_matcher:
            failed = intent.primary_locator.to_storage_string()
            candidates.extend(self._fuzzy_matcher.discover(page, failed))
        candidates.extend(self._discover_iframe_controls(page, intent))
        for frame in page.frames:
            candidates.extend(self._discover_in_frame(frame, intent, page))
        return self._dedupe(candidates)

    def _discover_iframe_controls(self, page: Page, intent: ElementIntent) -> list[LocatorCandidate]:
        """Priority candidates for controls that live only inside child frames."""
        results: list[LocatorCandidate] = []
        desc = intent.description.lower()
        for frame in page.frames:
            if frame == page.main_frame:
                continue
            frame_name = frame.name or None
            frame_url = frame.url or None
            meta = {"frame_name": frame_name, "frame_url": frame_url if not frame_name else None}

            if "registration" in desc or "submit" in desc or "action" in desc:
                results.append(
                    LocatorCandidate(
                        definition=LocatorDefinition(
                            strategy=LocatorStrategy.CSS,
                            value="#iframeRegisterBtn",
                            **meta,
                        ),
                        method=HealingMethod.HEURISTIC,
                        reason="Iframe submit button id heuristic",
                    )
                )
                results.append(
                    LocatorCandidate(
                        definition=LocatorDefinition(
                            strategy=LocatorStrategy.TEST_ID,
                            value="iframe-complete-btn",
                            **meta,
                        ),
                        method=HealingMethod.HEURISTIC,
                        reason="Iframe submit test id heuristic",
                    )
                )
                results.append(
                    LocatorCandidate(
                        definition=LocatorDefinition(
                            strategy=LocatorStrategy.ROLE,
                            value="role:button:Complete Registration",
                            role="button",
                            name="Complete Registration",
                            **meta,
                        ),
                        method=HealingMethod.HEURISTIC,
                        reason="Iframe complete registration button role",
                    )
                )
        return results

    def _discover_in_frame(
        self, frame: Page | Frame, intent: ElementIntent, page: Page
    ) -> list[LocatorCandidate]:
        results: list[LocatorCandidate] = []
        is_main = frame == page.main_frame
        frame_name = None if is_main else (frame.name or None)
        frame_url = None if is_main or frame_name else (frame.url or None)

        desc = intent.description
        keywords = self._keywords(desc)

        for role in ("button", "link", "textbox", "combobox", "checkbox", "radio"):
            for word in keywords:
                results.append(
                    LocatorCandidate(
                        definition=LocatorDefinition(
                            strategy=LocatorStrategy.ROLE,
                            value=f"role:{role}:{word}",
                            role=role,
                            name=word,
                            frame_name=frame_name,
                            frame_url=frame_url,
                        ),
                        method=HealingMethod.HEURISTIC,
                        reason=f"Role match for '{word}'",
                    )
                )

        for word in keywords:
            results.append(
                LocatorCandidate(
                    definition=LocatorDefinition(
                        strategy=LocatorStrategy.TEXT,
                        value=word,
                        frame_name=frame_name,
                        frame_url=frame_url,
                    ),
                    method=HealingMethod.HEURISTIC,
                    reason=f"Text match for '{word}'",
                )
            )
            results.append(
                LocatorCandidate(
                    definition=LocatorDefinition(
                        strategy=LocatorStrategy.LABEL,
                        value=word,
                        frame_name=frame_name,
                        frame_url=frame_url,
                    ),
                    method=HealingMethod.HEURISTIC,
                    reason=f"Label match for '{word}'",
                )
            )
            results.append(
                LocatorCandidate(
                    definition=LocatorDefinition(
                        strategy=LocatorStrategy.PLACEHOLDER,
                        value=word,
                        frame_name=frame_name,
                        frame_url=frame_url,
                    ),
                    method=HealingMethod.HEURISTIC,
                    reason=f"Placeholder match for '{word}'",
                )
            )

        if "registration" in desc.lower():
            results.append(
                LocatorCandidate(
                    definition=LocatorDefinition(
                        strategy=LocatorStrategy.ROLE,
                        value="role:button:Complete Registration",
                        role="button",
                        name="Complete Registration",
                        frame_name=frame_name,
                        frame_url=frame_url,
                    ),
                    method=HealingMethod.HEURISTIC,
                    reason="Complete registration button heuristic",
                )
            )

        if "submit" in desc.lower():
            results.append(
                LocatorCandidate(
                    definition=LocatorDefinition(
                        strategy=LocatorStrategy.ROLE,
                        value="role:button:Submit",
                        role="button",
                        name="Submit",
                        frame_name=frame_name,
                        frame_url=frame_url,
                    ),
                    method=HealingMethod.HEURISTIC,
                    reason="Submit button heuristic",
                )
            )
            results.append(
                LocatorCandidate(
                    definition=LocatorDefinition(
                        strategy=LocatorStrategy.CSS,
                        value="button[type='submit']",
                        frame_name=frame_name,
                        frame_url=frame_url,
                    ),
                    method=HealingMethod.HEURISTIC,
                    reason="Submit CSS heuristic",
                )
            )

        return results

    @staticmethod
    def _keywords(description: str) -> list[str]:
        stop = {"the", "used", "for", "button", "field", "input", "form", "to", "a", "an"}
        words = re.findall(r"[A-Za-z]{3,}", description)
        filtered = [w for w in words if w.lower() not in stop]
        if "submit" in description.lower() and "Submit" not in filtered:
            filtered.append("Submit")
        if "save" in description.lower() and "Save" not in filtered:
            filtered.append("Save")
        return filtered[:6]

    @staticmethod
    def _dedupe(candidates: list[LocatorCandidate]) -> list[LocatorCandidate]:
        seen: set[str] = set()
        unique: list[LocatorCandidate] = []
        for candidate in candidates:
            definition = candidate.definition
            key = "|".join(
                filter(
                    None,
                    [
                        definition.frame_name or "",
                        definition.frame_url or "",
                        definition.to_storage_string(),
                    ],
                )
            )
            if key not in seen:
                seen.add(key)
                unique.append(candidate)
        return unique
