from __future__ import annotations

from typing import Callable, Optional

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from framework.capture.context_collector import ContextCollector
from framework.capture.dom_pruner import DomPruner
from framework.config.settings import Settings, get_settings
from framework.healing.confidence_engine import ConfidenceEngine
from framework.healing.failure_classifier import FailureClassifier
from framework.healing.fuzzy_matcher import FuzzyMatcher
from framework.healing.heuristic_engine import HeuristicEngine
from framework.healing.orchestrator import HealingOrchestrator
from framework.healing.retry_manager import RetryManager
from framework.knowledge.sqlite_store import SQLiteLocatorRepository
from framework.llm.prompt_config import LlmPromptOverride
from framework.llm.provider_factory import create_llm_provider
from framework.logging.audit_logger import AuditLogger
from framework.models.domain import (
    ActionType,
    ElementIntent,
    ExecutionContext,
    HumanReviewRequiredError,
    LocatorDefinition,
)
from framework.utils.locator_resolver import LocatorResolver


class SelfHealingPage:
    """Playwright Page wrapper that triggers healing on locator failures."""

    def __init__(
        self,
        page: Page,
        execution: ExecutionContext,
        settings: Settings | None = None,
        orchestrator: HealingOrchestrator | None = None,
        llm_system_prompt: str | None = None,
        llm_user_context: str | None = None,
        llm_prompt: LlmPromptOverride | None = None,
    ) -> None:
        self._page = page
        self._execution = execution
        self._settings = settings or get_settings()
        self._llm_prompt = llm_prompt
        if self._llm_prompt is None and (llm_system_prompt or llm_user_context):
            self._llm_prompt = LlmPromptOverride(
                system_prompt=llm_system_prompt,
                user_context=llm_user_context,
            )
        self._audit_logger = AuditLogger(
            self._settings.artifacts_dir,
            echo_summary_to_console=self._settings.log_healing_summary_console,
        )
        self._orchestrator = orchestrator or self._build_default_orchestrator(self._audit_logger)
        self._retry_manager = RetryManager(self._settings.action_timeout_ms)
        self._attach_console_listener()

    @property
    def page(self) -> Page:
        return self._page

    @property
    def execution(self) -> ExecutionContext:
        return self._execution

    def set_llm_prompt(
        self,
        *,
        system_prompt: str | None = None,
        user_context: str | None = None,
    ) -> None:
        """Override LLM prompts from code (takes priority over .env / prompt files)."""
        if system_prompt is None and user_context is None:
            self._llm_prompt = None
            self._orchestrator.set_llm_prompt(None)
            return
        current = self._llm_prompt or LlmPromptOverride()
        self._llm_prompt = LlmPromptOverride(
            system_prompt=system_prompt if system_prompt is not None else current.system_prompt,
            user_context=user_context if user_context is not None else current.user_context,
        )
        self._orchestrator.set_llm_prompt(self._llm_prompt)

    def click(
        self,
        locator: str | LocatorDefinition,
        element_key: str,
        description: str,
        verify: Optional[Callable[[Page], None]] = None,
    ) -> None:
        self._run_action(
            ElementIntent(element_key, description, locator, ActionType.CLICK, verify=verify)
        )

    def fill(
        self,
        locator: str | LocatorDefinition,
        element_key: str,
        description: str,
        value: str,
    ) -> None:
        self._run_action(
            ElementIntent(
                element_key, description, locator, ActionType.FILL, action_value=value
            )
        )

    def select_option(
        self,
        locator: str | LocatorDefinition,
        element_key: str,
        description: str,
        value: str,
    ) -> None:
        self._run_action(
            ElementIntent(
                element_key,
                description,
                locator,
                ActionType.SELECT_OPTION,
                action_value=value,
            )
        )

    def _run_action(self, intent: ElementIntent) -> None:
        definition = intent.primary_locator
        attempts = 0
        last_error = ""

        while attempts < self._settings.max_heal_attempts:
            attempts += 1
            try:
                self._retry_manager.execute(self._page, intent, definition)
                if intent.verify:
                    intent.verify(self._page)
                self._record_primary_success(intent)
                return
            except HumanReviewRequiredError:
                return
            except (PlaywrightTimeoutError, AssertionError, Exception) as exc:
                last_error = str(exc)
                self._audit_logger.log(
                    "action_failed",
                    {
                        "execution_id": self._execution.execution_id,
                        "test_name": self._execution.test_name,
                        "element_key": intent.element_key,
                        "action": intent.action.value,
                        "locator": intent.primary_locator.to_storage_string(),
                        "error": last_error,
                        "heal_attempt": attempts,
                    },
                )
                try:
                    result = self._orchestrator.heal(
                        self._page, intent, self._execution, last_error
                    )
                except HumanReviewRequiredError:
                    return
                if result.success and result.candidate:
                    # Orchestrator already executed the action and verify hook.
                    self._record_healed_success(
                        intent,
                        result.candidate.definition,
                        confidence=result.confidence,
                    )
                    return
                # One heal pass already tried history, heuristics, fuzzy, and LLM.
                # Re-running the same primary locator + heal cycle is not useful.
                break

        raise PlaywrightTimeoutError(
            f"Action failed for '{intent.element_key}' after healing attempts: {last_error}"
        )

    def _record_primary_success(self, intent: ElementIntent) -> None:
        self._record_healed_success(intent, intent.primary_locator, confidence=100.0)

    def _record_healed_success(
        self,
        intent: ElementIntent,
        locator: LocatorDefinition,
        confidence: float = 100.0,
    ) -> None:
        repository = SQLiteLocatorRepository(self._settings.sqlite_path)
        page_key = HealingOrchestrator._page_key(self._page)
        stored = locator.to_storage_string()
        repository.promote_locator(
            self._execution.application_id,
            page_key,
            intent.element_key,
            locator,
            confidence,
        )
        repository.append_history(
            self._execution.application_id,
            page_key,
            intent.element_key,
            stored,
            True,
        )

    def _build_default_orchestrator(self, audit: AuditLogger) -> HealingOrchestrator:
        settings = self._settings
        repository = SQLiteLocatorRepository(settings.sqlite_path)
        return HealingOrchestrator(
            settings=settings,
            repository=repository,
            context_collector=ContextCollector(settings, repository, DomPruner(settings.dom_prune_max_bytes)),
            heuristic_engine=HeuristicEngine(
                fuzzy_matcher=FuzzyMatcher(settings.fuzzy_match_threshold)
                if settings.fuzzy_match_enabled
                else None
            ),
            failure_classifier=FailureClassifier(),
            confidence_engine=ConfidenceEngine(settings),
            retry_manager=RetryManager(settings.action_timeout_ms),
            llm_provider=create_llm_provider(settings, self._llm_prompt),
            audit_logger=audit,
        )

    def _attach_console_listener(self) -> None:
        logs: list[str] = []
        self._page._healing_console_logs = logs  # type: ignore[attr-defined]

        def _on_console(msg) -> None:
            logs.append(f"{msg.type}: {msg.text}")

        self._page.on("console", _on_console)
