from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from framework.logging.healing_log_formatter import FAILURE_CATEGORY_LABELS, build_healing_summary
from framework.models.domain import (
    ElementIntent,
    ExecutionContext,
    FailureCategory,
    HealingResult,
    LocatorCandidate,
)
from framework.logging.healing_trace import HealingTrace


class AuditLogger:
    def __init__(self, artifacts_dir: Path, echo_summary_to_console: bool = False) -> None:
        self._log_dir = artifacts_dir / "logs"
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._log_file = self._log_dir / "healing_audit.jsonl"
        self._echo_summary_to_console = echo_summary_to_console

    def log(self, event_type: str, payload: dict[str, Any]) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            **payload,
        }
        line = json.dumps(record, default=str)
        with self._log_file.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def log_healing_outcome(
        self,
        execution: ExecutionContext,
        intent: ElementIntent,
        *,
        failure_category: FailureCategory,
        original_error: str,
        failed_locator: str,
        trace: HealingTrace,
        result: HealingResult | None,
        healing_succeeded: bool,
        html_snapshot_path: str | None = None,
        screenshot_path: str | None = None,
    ) -> None:
        from framework.logging.healing_log_formatter import candidate_to_audit_dict

        llm_proposal_dict = (
            candidate_to_audit_dict(trace.llm_proposal) if trace.llm_proposal else None
        )
        applied = None
        if result and result.candidate:
            applied = candidate_to_audit_dict(result.candidate)

        solved_by_llm = bool(
            healing_succeeded and result and result.method.value == "llm"
        )

        summary = build_healing_summary(
            failure_category=failure_category,
            failed_locator=failed_locator,
            result=result,
            llm_invoked=trace.llm_invoked,
            llm_proposed=trace.llm_proposal,
            healing_succeeded=healing_succeeded,
        )

        payload = {
            "execution_id": execution.execution_id,
            "test_name": execution.test_name,
            "application_id": execution.application_id,
            "environment": execution.environment,
            "element_key": intent.element_key,
            "element_description": intent.description,
            "action": intent.action.value,
            "failure_category": failure_category.value,
            "failure_category_label": FAILURE_CATEGORY_LABELS.get(
                failure_category, failure_category.value
            ),
            "original_error": original_error,
            "failed_locator": failed_locator,
            "healing_succeeded": healing_succeeded,
            "solved_by_llm": solved_by_llm,
            "healing_method": result.method.value if result else "none",
            "confidence": result.confidence if result else 0.0,
            "healing_status": result.status.value if result else "failed",
            "llm_invoked": trace.llm_invoked,
            "llm_proposal": llm_proposal_dict,
            "llm_error": trace.llm_error,
            "applied_locator": applied,
            "deterministic_candidates_found": trace.deterministic_candidates_found,
            "proposals_tried": trace.proposals_tried,
            "proposals_rejected": trace.proposals_rejected,
            "html_snapshot_path": html_snapshot_path,
            "screenshot_path": screenshot_path,
            "summary": summary,
        }

        self.log("healing_outcome", payload)
        if self._echo_summary_to_console:
            print(f"[healing] {summary}", file=sys.stderr)
