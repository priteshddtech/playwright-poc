from __future__ import annotations

from dataclasses import dataclass, field

from framework.models.domain import FailureCategory, LocatorCandidate


@dataclass
class HealingTrace:
    """Collects healing attempt details for a single audit outcome record."""

    failure_category: FailureCategory = FailureCategory.UNKNOWN
    llm_invoked: bool = False
    llm_proposal: LocatorCandidate | None = None
    llm_error: str | None = None
    deterministic_candidates_found: int = 0
    proposals_tried: list[dict] = field(default_factory=list)
    proposals_rejected: list[dict] = field(default_factory=list)

    def record_candidate_attempt(self, candidate: LocatorCandidate, outcome: dict) -> None:
        entry = {
            "proposal": candidate.method.value,
            **outcome,
        }
        if outcome.get("accepted"):
            self.proposals_tried.append(entry)
        else:
            self.proposals_rejected.append(entry)
