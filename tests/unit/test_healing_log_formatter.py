from framework.logging.healing_log_formatter import (
    FAILURE_CATEGORY_LABELS,
    build_healing_summary,
)
from framework.models.domain import (
    FailureCategory,
    HealingMethod,
    HealingResult,
    HealingStatus,
    LocatorCandidate,
    LocatorDefinition,
    LocatorStrategy,
)


def test_build_summary_healed_by_llm() -> None:
    result = HealingResult(
        success=True,
        candidate=LocatorCandidate(
            definition=LocatorDefinition(strategy=LocatorStrategy.CSS, value="#newBtn"),
            method=HealingMethod.LLM,
        ),
        method=HealingMethod.LLM,
        confidence=96.0,
        status=HealingStatus.SUCCESS,
    )
    summary = build_healing_summary(
        failure_category=FailureCategory.LOCATOR_MISSING,
        failed_locator="#submitButton",
        result=result,
        llm_invoked=True,
        llm_proposed=result.candidate,
        healing_succeeded=True,
    )
    assert "HEALED" in summary
    assert "LLM" in summary
    assert "#newBtn" in summary


def test_failure_category_labels_cover_missing() -> None:
    assert FailureCategory.LOCATOR_MISSING in FAILURE_CATEGORY_LABELS
