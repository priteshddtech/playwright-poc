from __future__ import annotations

import re
from difflib import SequenceMatcher

from playwright.sync_api import Frame, Page

from framework.models.domain import HealingMethod, LocatorCandidate, LocatorDefinition, LocatorStrategy

_EXTRACT_ATTRIBUTES_JS = """
() => {
  const results = [];
  const selector = 'input, select, textarea, button, a, [id], [name], [data-testid]';
  for (const el of document.querySelectorAll(selector)) {
    results.push({
      id: el.id || '',
      name: el.getAttribute('name') || '',
      testId: el.getAttribute('data-testid') || '',
    });
  }
  return results;
}
"""


class FuzzyMatcher:
    """Find locators when ids/names change slightly (e.g. firstName -> first_name)."""

    def __init__(self, threshold: float = 0.85) -> None:
        self._threshold = threshold

    def discover(self, page: Page, failed_locator: str) -> list[LocatorCandidate]:
        hint = self.extract_hint(failed_locator)
        if not hint or len(hint) < 2:
            return []

        hint_norm = normalize_attribute_token(hint)
        candidates: list[LocatorCandidate] = []

        for frame in page.frames:
            frame_name = None if frame == page.main_frame else (frame.name or None)
            frame_url = None if frame == page.main_frame or frame_name else (frame.url or None)
            try:
                attributes = frame.evaluate(_EXTRACT_ATTRIBUTES_JS)
            except Exception:
                continue

            for entry in attributes:
                candidate = self._match_entry(
                    entry, hint, hint_norm, frame_name, frame_url
                )
                if candidate:
                    candidates.append(candidate)

        return self._dedupe_by_score(candidates)

    @staticmethod
    def extract_hint(failed_locator: str) -> str:
        raw = failed_locator.strip()
        if raw.startswith("#"):
            return raw[1:].split(".")[0].split("[")[0]
        name_match = re.search(r"""name=['"]([^'"]+)['"]""", raw)
        if name_match:
            return name_match.group(1)
        test_id_match = re.search(r"""data-testid=['"]([^'"]+)['"]""", raw)
        if test_id_match:
            return test_id_match.group(1)
        class_match = re.search(r"""\.([A-Za-z_][\w-]*)""", raw)
        if class_match:
            return class_match.group(1)
        return raw

    def _match_entry(
        self,
        entry: dict,
        hint: str,
        hint_norm: str,
        frame_name: str | None,
        frame_url: str | None,
    ) -> LocatorCandidate | None:
        best_ratio = 0.0
        best_attr = ""
        best_value = ""

        for attr_key, attr_name in (("id", "id"), ("name", "name"), ("testId", "data-testid")):
            value = str(entry.get(attr_key) or "")
            if not value or value == hint:
                continue
            ratio = similarity_ratio(hint, value)
            if ratio > best_ratio:
                best_ratio = ratio
                best_attr = attr_name
                best_value = value

        if best_ratio < self._threshold:
            return None

        definition = self._to_locator_definition(
            best_attr, best_value, frame_name, frame_url
        )
        return LocatorCandidate(
            definition=definition,
            method=HealingMethod.FUZZY,
            llm_confidence=round(best_ratio * 100, 2),
            reason=f"Fuzzy {best_attr} match '{hint}' ~ '{best_value}' ({best_ratio:.2f})",
        )

    @staticmethod
    def _to_locator_definition(
        attr: str,
        value: str,
        frame_name: str | None,
        frame_url: str | None,
    ) -> LocatorDefinition:
        if attr == "id":
            css = f"#{value}"
        elif attr == "name":
            css = f'[name="{value}"]'
        else:
            return LocatorDefinition(
                strategy=LocatorStrategy.TEST_ID,
                value=value,
                frame_name=frame_name,
                frame_url=frame_url,
            )
        return LocatorDefinition(
            strategy=LocatorStrategy.CSS,
            value=css,
            frame_name=frame_name,
            frame_url=frame_url,
        )

    @staticmethod
    def _dedupe_by_score(candidates: list[LocatorCandidate]) -> list[LocatorCandidate]:
        best: dict[str, LocatorCandidate] = {}
        for candidate in candidates:
            key = candidate.definition.to_storage_string()
            if (
                key not in best
                or (candidate.llm_confidence or 0) > (best[key].llm_confidence or 0)
            ):
                best[key] = candidate
        return sorted(best.values(), key=lambda c: c.llm_confidence or 0, reverse=True)


def normalize_attribute_token(value: str) -> str:
    """Normalize id/name tokens so firstName and first_name compare equal."""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    spaced = spaced.replace("_", " ").replace("-", " ")
    return re.sub(r"[^a-z0-9]", "", spaced.lower())


def similarity_ratio(left: str, right: str) -> float:
    left_norm = normalize_attribute_token(left)
    right_norm = normalize_attribute_token(right)
    if not left_norm or not right_norm:
        return 0.0
    if left_norm == right_norm:
        return 1.0
    return SequenceMatcher(None, left_norm, right_norm).ratio()
