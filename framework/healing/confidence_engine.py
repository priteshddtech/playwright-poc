from __future__ import annotations

from playwright.sync_api import Page

from framework.config.settings import Settings
from framework.models.domain import ElementIntent, HealingMethod, LocatorCandidate, ValidationResult
from framework.utils.locator_resolver import LocatorResolver


class ConfidenceEngine:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def validate(
        self,
        page: Page,
        intent: ElementIntent,
        candidate: LocatorCandidate,
        historical_locators: list[str],
    ) -> ValidationResult:
        locator = LocatorResolver.resolve(page, candidate.definition)
        try:
            count = locator.count()
        except Exception as exc:
            return ValidationResult(
                is_valid=False,
                match_count=0,
                is_visible=False,
                is_enabled=False,
                confidence=0.0,
                message=str(exc),
            )

        if count != 1:
            return ValidationResult(
                is_valid=False,
                match_count=count,
                is_visible=False,
                is_enabled=False,
                confidence=0.0,
                message=f"Expected 1 match, found {count}",
            )

        try:
            is_visible = locator.is_visible()
            is_enabled = locator.is_enabled()
        except Exception:
            is_visible = False
            is_enabled = False

        semantic = self._semantic_score(intent.description, candidate)
        accessibility = 100.0 if candidate.definition.strategy.value == "role" else 60.0
        dom_context = 70.0
        uniqueness = 100.0 if count == 1 else 0.0
        visibility = 100.0 if is_visible and is_enabled else 30.0
        history = (
            100.0
            if candidate.definition.to_storage_string() in historical_locators
            else 40.0
        )

        signals = {
            "semantic": semantic,
            "accessibility": accessibility,
            "dom_context": dom_context,
            "uniqueness": uniqueness,
            "visibility": visibility,
            "history": history,
        }

        weights = {
            "semantic": self._settings.weight_semantic,
            "accessibility": self._settings.weight_accessibility,
            "dom_context": self._settings.weight_dom_context,
            "uniqueness": self._settings.weight_uniqueness,
            "visibility": self._settings.weight_visibility,
            "history": self._settings.weight_history,
        }

        confidence = sum(signals[k] * weights[k] for k in signals)

        if candidate.llm_confidence is not None and count == 1 and is_visible:
            confidence = max(confidence, candidate.llm_confidence)

        if (
            count == 1
            and is_visible
            and (candidate.definition.frame_name or candidate.definition.frame_url)
        ):
            confidence = max(confidence, 88.0)

        if candidate.method == HealingMethod.FUZZY and count == 1 and is_visible:
            fuzzy_score = candidate.llm_confidence or 85.0
            confidence = max(confidence, min(98.0, fuzzy_score + 5.0))

        is_valid = is_visible and count == 1 and confidence >= self._settings.confidence_warn

        return ValidationResult(
            is_valid=is_valid,
            match_count=count,
            is_visible=is_visible,
            is_enabled=is_enabled,
            confidence=round(confidence, 2),
            signals=signals,
            message="Validation complete",
        )

    @staticmethod
    def _semantic_score(description: str, candidate: LocatorCandidate) -> float:
        desc = description.lower()
        if candidate.definition.name and candidate.definition.name.lower() in desc:
            return 95.0
        tokens = [t for t in desc.split() if len(t) > 2]
        haystack = " ".join(
            filter(
                None,
                [
                    candidate.definition.value,
                    candidate.definition.name or "",
                    candidate.reason,
                ],
            )
        ).lower()
        if not tokens:
            return 50.0
        hits = sum(1 for t in tokens if t in haystack)
        return min(100.0, (hits / len(tokens)) * 100.0 + 20.0)
