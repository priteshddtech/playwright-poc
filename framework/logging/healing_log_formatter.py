from __future__ import annotations

from framework.models.domain import (
    FailureCategory,
    HealingMethod,
    HealingResult,
    LocatorCandidate,
    LocatorDefinition,
)

FAILURE_CATEGORY_LABELS: dict[FailureCategory, str] = {
    FailureCategory.TIMING: "Timing / element not yet visible",
    FailureCategory.LOCATOR_MISSING: "Locator missing (element not in DOM)",
    FailureCategory.LOCATOR_CHANGED: "Locator changed or no longer valid",
    FailureCategory.IFRAME_CHANGED: "Element moved to or inside iframe",
    FailureCategory.UI_CHANGED: "UI structure changed",
    FailureCategory.BUSINESS_LOGIC: "Control removed or business logic changed",
    FailureCategory.UNKNOWN: "Unknown failure",
}


def locator_to_audit_dict(definition: LocatorDefinition) -> dict[str, str | None]:
    return {
        "strategy": definition.strategy.value,
        "locator": definition.to_storage_string(),
        "frame_name": definition.frame_name,
        "frame_url": definition.frame_url,
        "role": definition.role,
        "name": definition.name,
    }


def candidate_to_audit_dict(candidate: LocatorCandidate) -> dict:
    payload = {
        "healing_method": candidate.method.value,
        "reason": candidate.reason,
        "confidence_hint": candidate.llm_confidence,
        **locator_to_audit_dict(candidate.definition),
    }
    return payload


def build_healing_summary(
    *,
    failure_category: FailureCategory,
    failed_locator: str,
    result: HealingResult | None,
    llm_invoked: bool,
    llm_proposed: LocatorCandidate | None,
    healing_succeeded: bool,
) -> str:
    label = FAILURE_CATEGORY_LABELS.get(failure_category, failure_category.value)
    if healing_succeeded and result and result.candidate:
        method = result.method.value
        healed = result.candidate.definition.to_storage_string()
        llm_note = " (LLM)" if result.method == HealingMethod.LLM else ""
        return (
            f"HEALED [{label}] failed locator '{failed_locator}' → "
            f"'{healed}' via {method}{llm_note} (confidence {result.confidence}%)"
        )
    if llm_invoked and llm_proposed:
        proposed = llm_proposed.definition.to_storage_string()
        return (
            f"NOT HEALED [{label}] failed locator '{failed_locator}'. "
            f"LLM proposed '{proposed}' but it did not pass validation/execution."
        )
    if llm_invoked:
        return (
            f"NOT HEALED [{label}] failed locator '{failed_locator}'. "
            "LLM was invoked but returned no usable proposal."
        )
    return (
        f"NOT HEALED [{label}] failed locator '{failed_locator}'. "
        "Heuristics/history/fuzzy did not produce a working locator."
    )
