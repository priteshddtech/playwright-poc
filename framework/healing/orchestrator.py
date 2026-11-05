from __future__ import annotations

from playwright.sync_api import Page

from framework.capture.context_collector import ContextCollector
from framework.config.settings import Settings
from framework.healing.confidence_engine import ConfidenceEngine
from framework.healing.failure_classifier import FailureClassifier
from framework.healing.heuristic_engine import HeuristicEngine
from framework.healing.retry_manager import RetryManager
from framework.knowledge.locator_repository import LocatorRepository
from framework.llm.base_provider import LLMProvider
from framework.logging.audit_logger import AuditLogger
from framework.logging.healing_log_formatter import (
    FAILURE_CATEGORY_LABELS,
    candidate_to_audit_dict,
)
from framework.logging.healing_trace import HealingTrace
from framework.models.domain import (
    ElementIntent,
    ExecutionContext,
    FailureCategory,
    FailureContext,
    HealingEventRecord,
    HealingMethod,
    HealingResult,
    HealingStatus,
    HumanReviewRequiredError,
    LocatorCandidate,
    LocatorDefinition,
)
from framework.utils.locator_resolver import LocatorResolver


class HealingOrchestrator:
    def __init__(
        self,
        settings: Settings,
        repository: LocatorRepository,
        context_collector: ContextCollector,
        heuristic_engine: HeuristicEngine,
        failure_classifier: FailureClassifier,
        confidence_engine: ConfidenceEngine,
        retry_manager: RetryManager,
        llm_provider: LLMProvider,
        audit_logger: AuditLogger,
    ) -> None:
        self._settings = settings
        self._repository = repository
        self._context_collector = context_collector
        self._heuristic_engine = heuristic_engine
        self._failure_classifier = failure_classifier
        self._confidence_engine = confidence_engine
        self._retry_manager = retry_manager
        self._llm_provider = llm_provider
        self._audit = audit_logger

    def heal(
        self,
        page: Page,
        intent: ElementIntent,
        execution: ExecutionContext,
        error_message: str,
    ) -> HealingResult:
        trace = HealingTrace()
        page_key = self._page_key(page)
        failure_context = self._context_collector.collect(
            page,
            intent,
            execution.application_id,
            page_key,
            error_message,
        )

        category = self._failure_classifier.classify(failure_context)
        category = self._failure_classifier.refine_with_page(page, intent, category)
        trace.failure_category = category

        self._audit.log(
            "failure_classified",
            {
                "execution_id": execution.execution_id,
                "element_key": intent.element_key,
                "failure_category": category.value,
                "failure_category_label": FAILURE_CATEGORY_LABELS.get(category, category.value),
                "original_error": error_message,
                "failed_locator": failure_context.failed_locator,
                "url": failure_context.url,
                "page_title": failure_context.title,
                "frame_count": len(failure_context.frames),
            },
        )

        self._audit.log(
            "healing_started",
            {
                "execution_id": execution.execution_id,
                "test_name": execution.test_name,
                "element_key": intent.element_key,
                "element_description": intent.description,
                "action": intent.action.value,
                "failed_locator": failure_context.failed_locator,
                "failure_category": category.value,
                "original_error": error_message,
                "url": failure_context.url,
                "html_snapshot_path": failure_context.html_snapshot_path,
                "screenshot_path": failure_context.screenshot_path,
            },
        )

        candidates = self._build_candidate_list(page, intent, execution, page_key)
        trace.deterministic_candidates_found = len(candidates)

        self._audit.log(
            "candidates_discovered",
            {
                "execution_id": execution.execution_id,
                "element_key": intent.element_key,
                "count": len(candidates),
                "proposals": [candidate_to_audit_dict(c) for c in candidates[:15]],
            },
        )

        if category == FailureCategory.TIMING:
            if self._retry_manager.smart_wait_retry(page, intent):
                result = HealingResult(
                    success=True,
                    candidate=LocatorCandidate(
                        definition=intent.primary_locator,
                        method=HealingMethod.TIMING_RETRY,
                    ),
                    method=HealingMethod.TIMING_RETRY,
                    confidence=100.0,
                    status=HealingStatus.SUCCESS,
                    message="Recovered via smart wait retry",
                )
                self._persist_success(page, intent, execution, page_key, result)
                self._log_outcome(
                    execution,
                    intent,
                    category,
                    error_message,
                    failure_context,
                    trace,
                    result,
                    True,
                )
                return result

        if category == FailureCategory.BUSINESS_LOGIC:
            self._record_event(
                execution, intent, failure_context.failed_locator, None, 0.0, "failed", "none"
            )
            failed = HealingResult(
                success=False,
                candidate=None,
                method=HealingMethod.NONE,
                confidence=0.0,
                status=HealingStatus.FAILED,
                message="Business logic change suspected",
            )
            self._log_outcome(
                execution,
                intent,
                category,
                error_message,
                failure_context,
                trace,
                failed,
                False,
            )
            raise HumanReviewRequiredError("Element appears removed; human review required.")

        healed = self._try_candidates(
            page, intent, execution, page_key, failure_context, candidates, trace
        )
        if healed:
            self._log_outcome(
                execution,
                intent,
                category,
                error_message,
                failure_context,
                trace,
                healed,
                True,
            )
            return healed

        if not self._llm_provider.is_available():
            reason = getattr(self._llm_provider, "unavailable_reason", "LLM not available")
            self._audit.log(
                "llm_skipped",
                {
                    "execution_id": execution.execution_id,
                    "element_key": intent.element_key,
                    "reason": reason,
                    "failure_category": category.value,
                },
            )
            llm_candidate = None
        else:
            trace.llm_invoked = True
            self._audit.log(
                "llm_invoked",
                {
                    "execution_id": execution.execution_id,
                    "element_key": intent.element_key,
                    "reason": "Deterministic strategies exhausted",
                    "failure_category": category.value,
                },
            )

            try:
                llm_candidate = self._llm_provider.discover_locator(intent, failure_context)
            except Exception as exc:
                trace.llm_error = str(exc)
                llm_candidate = None
                self._audit.log(
                    "llm_error",
                    {
                        "execution_id": execution.execution_id,
                        "element_key": intent.element_key,
                        "error": str(exc),
                    },
                )

        if llm_candidate:
            trace.llm_proposal = llm_candidate
            self._audit.log(
                "llm_proposal",
                {
                    "execution_id": execution.execution_id,
                    "element_key": intent.element_key,
                    "proposal": candidate_to_audit_dict(llm_candidate),
                },
            )
            llm_result = self._try_candidates(
                page,
                intent,
                execution,
                page_key,
                failure_context,
                [llm_candidate],
                trace,
            )
            if llm_result:
                self._log_outcome(
                    execution,
                    intent,
                    category,
                    error_message,
                    failure_context,
                    trace,
                    llm_result,
                    True,
                )
                return llm_result
        else:
            self._audit.log(
                "llm_no_proposal",
                {
                    "execution_id": execution.execution_id,
                    "element_key": intent.element_key,
                },
            )

        self._record_event(
            execution,
            intent,
            failure_context.failed_locator,
            None,
            0.0,
            HealingStatus.FAILED.value,
            HealingMethod.NONE.value,
        )
        failed = HealingResult(
            success=False,
            candidate=None,
            method=HealingMethod.NONE,
            confidence=0.0,
            status=HealingStatus.FAILED,
            message="All healing strategies exhausted",
        )
        self._log_outcome(
            execution,
            intent,
            category,
            error_message,
            failure_context,
            trace,
            failed,
            False,
        )
        return failed

    def _log_outcome(
        self,
        execution: ExecutionContext,
        intent: ElementIntent,
        category: FailureCategory,
        error_message: str,
        failure_context: FailureContext,
        trace: HealingTrace,
        result: HealingResult | None,
        healing_succeeded: bool,
    ) -> None:
        trace.failure_category = category
        self._audit.log_healing_outcome(
            execution,
            intent,
            failure_category=category,
            original_error=error_message,
            failed_locator=failure_context.failed_locator,
            trace=trace,
            result=result,
            healing_succeeded=healing_succeeded,
            html_snapshot_path=failure_context.html_snapshot_path,
            screenshot_path=failure_context.screenshot_path,
        )

    def _try_candidates(
        self,
        page: Page,
        intent: ElementIntent,
        execution: ExecutionContext,
        page_key: str,
        failure_context: FailureContext,
        candidates: list[LocatorCandidate],
        trace: HealingTrace,
    ) -> HealingResult | None:
        for candidate in candidates[: self._settings.max_candidates]:
            validation = self._confidence_engine.validate(
                page,
                intent,
                candidate,
                failure_context.historical_locators,
            )
            proposal = candidate_to_audit_dict(candidate)
            self._audit.log(
                "candidate_validated",
                {
                    "execution_id": execution.execution_id,
                    "element_key": intent.element_key,
                    "proposal": proposal,
                    "confidence": validation.confidence,
                    "valid": validation.is_valid,
                    "match_count": validation.match_count,
                    "is_visible": validation.is_visible,
                    "validation_message": validation.message,
                },
            )

            if validation.confidence < self._settings.confidence_warn:
                trace.record_candidate_attempt(
                    candidate,
                    {
                        "locator": proposal["locator"],
                        "accepted": False,
                        "reason": f"Confidence {validation.confidence} below threshold",
                    },
                )
                continue

            try:
                self._retry_manager.execute(page, intent, candidate.definition)
                if intent.verify:
                    intent.verify(page)

                status = HealingStatus.SUCCESS
                if validation.confidence < self._settings.confidence_warn:
                    status = HealingStatus.PENDING_REVIEW

                result = HealingResult(
                    success=True,
                    candidate=candidate,
                    method=candidate.method,
                    confidence=validation.confidence,
                    status=status,
                    message=validation.message,
                )
                self._persist_success(page, intent, execution, page_key, result)
                trace.record_candidate_attempt(
                    candidate,
                    {
                        "locator": proposal["locator"],
                        "accepted": True,
                        "confidence": validation.confidence,
                        "healing_method": candidate.method.value,
                    },
                )

                if validation.confidence < self._settings.confidence_auto_heal:
                    self._audit.log(
                        "healing_medium_confidence",
                        {
                            "execution_id": execution.execution_id,
                            "element_key": intent.element_key,
                            "proposal": proposal,
                            "confidence": validation.confidence,
                            "message": "Auto-healed with medium confidence; review recommended.",
                        },
                    )

                if status == HealingStatus.PENDING_REVIEW:
                    self._record_event(
                        execution,
                        intent,
                        failure_context.failed_locator,
                        candidate.definition.to_storage_string(),
                        validation.confidence,
                        HealingStatus.PENDING_REVIEW.value,
                        candidate.method.value,
                    )
                    raise HumanReviewRequiredError(
                        f"Healed with low confidence ({validation.confidence}); human review required."
                    )

                return result
            except HumanReviewRequiredError:
                raise
            except Exception as exc:
                trace.record_candidate_attempt(
                    candidate,
                    {
                        "locator": proposal["locator"],
                        "accepted": False,
                        "reason": str(exc),
                    },
                )
                self._audit.log(
                    "candidate_execution_failed",
                    {
                        "execution_id": execution.execution_id,
                        "element_key": intent.element_key,
                        "proposal": proposal,
                        "error": str(exc),
                    },
                )
                continue
        return None

    def _build_candidate_list(
        self,
        page: Page,
        intent: ElementIntent,
        execution: ExecutionContext,
        page_key: str,
    ) -> list[LocatorCandidate]:
        candidates: list[LocatorCandidate] = []

        stored = self._repository.get_current(
            execution.application_id, page_key, intent.element_key
        )
        if stored:
            candidates.append(
                LocatorCandidate(
                    definition=stored, method=HealingMethod.HISTORY, reason="Stored locator"
                )
            )

        for raw in self._repository.get_history(execution.application_id, page_key, intent.element_key):
            candidates.append(
                LocatorCandidate(
                    definition=LocatorDefinition.from_storage_string(raw),
                    method=HealingMethod.HISTORY,
                    reason="Historical locator",
                )
            )

        candidates.extend(self._heuristic_engine.discover(page, intent))

        seen: set[str] = set()
        unique: list[LocatorCandidate] = []
        for candidate in candidates:
            key = candidate.definition.to_storage_string()
            if key in seen:
                continue
            seen.add(key)
            if self._quick_resolve(page, candidate):
                unique.append(candidate)
        return unique

    @staticmethod
    def _quick_resolve(page: Page, candidate: LocatorCandidate) -> bool:
        try:
            locator = LocatorResolver.resolve(page, candidate.definition)
            return locator.count() >= 1
        except Exception:
            return False

    def _persist_success(
        self,
        page: Page,
        intent: ElementIntent,
        execution: ExecutionContext,
        page_key: str,
        result: HealingResult,
    ) -> None:
        if not result.candidate:
            return
        stored = result.candidate.definition.to_storage_string()
        self._repository.promote_locator(
            execution.application_id,
            page_key,
            intent.element_key,
            result.candidate.definition,
            result.confidence,
        )
        self._repository.append_history(
            execution.application_id,
            page_key,
            intent.element_key,
            stored,
            True,
        )
        self._record_event(
            execution,
            intent,
            intent.primary_locator.to_storage_string(),
            stored,
            result.confidence,
            result.status.value,
            result.method.value,
        )
        self._audit.log(
            "healing_success",
            {
                "execution_id": execution.execution_id,
                "element_key": intent.element_key,
                "failed_locator": intent.primary_locator.to_storage_string(),
                "applied_locator": stored,
                "healing_method": result.method.value,
                "solved_by_llm": result.method == HealingMethod.LLM,
                "confidence": result.confidence,
            },
        )

    def _record_event(
        self,
        execution: ExecutionContext,
        intent: ElementIntent,
        failed: str,
        healed: str | None,
        confidence: float,
        status: str,
        method: str,
    ) -> None:
        self._repository.record_healing_event(
            HealingEventRecord(
                execution_id=execution.execution_id,
                element_key=intent.element_key,
                failed_locator=failed,
                healed_locator=healed,
                confidence=confidence,
                status=status,
                healing_method=method,
            )
        )

    @staticmethod
    def _page_key(page: Page) -> str:
        url = page.url
        if url.startswith("file:"):
            return url.split("/")[-1]
        return url
