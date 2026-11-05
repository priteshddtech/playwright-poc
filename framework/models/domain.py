from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

from playwright.sync_api import Page


class LocatorStrategy(str, Enum):
    CSS = "css"
    ROLE = "role"
    TEXT = "text"
    LABEL = "label"
    PLACEHOLDER = "placeholder"
    TEST_ID = "test_id"


class ActionType(str, Enum):
    CLICK = "click"
    FILL = "fill"
    SELECT_OPTION = "select_option"
    CHECK = "check"
    UNCHECK = "uncheck"
    PRESS = "press"


class HealingMethod(str, Enum):
    PRIMARY = "primary"
    HISTORY = "history"
    HEURISTIC = "heuristic"
    FUZZY = "fuzzy"
    TIMING_RETRY = "timing_retry"
    LLM = "llm"
    NONE = "none"


class HealingStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PENDING_REVIEW = "pending_review"


class FailureCategory(str, Enum):
    TIMING = "timing"
    LOCATOR_MISSING = "locator_missing"
    LOCATOR_CHANGED = "locator_changed"
    IFRAME_CHANGED = "iframe_changed"
    UI_CHANGED = "ui_changed"
    BUSINESS_LOGIC = "business_logic"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class LocatorDefinition:
    strategy: LocatorStrategy
    value: str
    role: Optional[str] = None
    name: Optional[str] = None
    frame_name: Optional[str] = None
    frame_url: Optional[str] = None

    def to_storage_string(self) -> str:
        if self.strategy == LocatorStrategy.CSS:
            return self.value
        if self.strategy == LocatorStrategy.ROLE:
            return f"role:{self.role}:{self.name or ''}"
        return f"{self.strategy.value}:{self.value}"

    @classmethod
    def from_storage_string(cls, raw: str) -> LocatorDefinition:
        if raw.startswith("role:"):
            parts = raw.split(":", 2)
            role = parts[1] if len(parts) > 1 else "button"
            name = parts[2] if len(parts) > 2 else ""
            return cls(strategy=LocatorStrategy.ROLE, value=raw, role=role, name=name or None)
        if raw.startswith("text:"):
            return cls(strategy=LocatorStrategy.TEXT, value=raw.removeprefix("text:"))
        if raw.startswith("label:"):
            return cls(strategy=LocatorStrategy.LABEL, value=raw.removeprefix("label:"))
        if raw.startswith("placeholder:"):
            return cls(strategy=LocatorStrategy.PLACEHOLDER, value=raw.removeprefix("placeholder:"))
        if raw.startswith("test_id:"):
            return cls(strategy=LocatorStrategy.TEST_ID, value=raw.removeprefix("test_id:"))
        return cls(strategy=LocatorStrategy.CSS, value=raw)


@dataclass(frozen=True)
class ElementIntent:
    element_key: str
    description: str
    locator: str | LocatorDefinition
    action: ActionType
    action_value: Optional[str] = None
    verify: Optional[Callable[[Page], None]] = None

    @property
    def primary_locator(self) -> LocatorDefinition:
        if isinstance(self.locator, LocatorDefinition):
            return self.locator
        return LocatorDefinition(strategy=LocatorStrategy.CSS, value=self.locator)


@dataclass(frozen=True)
class ExecutionContext:
    execution_id: str
    test_name: str
    application_id: str
    environment: str


@dataclass
class FrameInfo:
    name: str
    url: str
    index: int


@dataclass
class FailureContext:
    url: str
    title: str
    html_pruned: str
    html_snapshot_path: Optional[str]
    screenshot_path: Optional[str]
    accessibility_tree: Any
    frames: list[FrameInfo]
    console_logs: list[str]
    failed_locator: str
    error_message: str
    historical_locators: list[str] = field(default_factory=list)


@dataclass
class LocatorCandidate:
    definition: LocatorDefinition
    method: HealingMethod
    llm_confidence: Optional[float] = None
    reason: str = ""


@dataclass
class ValidationResult:
    is_valid: bool
    match_count: int
    is_visible: bool
    is_enabled: bool
    confidence: float
    signals: dict[str, float] = field(default_factory=dict)
    message: str = ""


@dataclass
class HealingResult:
    success: bool
    candidate: Optional[LocatorCandidate]
    method: HealingMethod
    confidence: float
    status: HealingStatus
    message: str = ""


@dataclass
class HealingEventRecord:
    execution_id: str
    element_key: str
    failed_locator: str
    healed_locator: Optional[str]
    confidence: float
    status: str
    healing_method: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class HumanReviewRequiredError(Exception):
    """Raised when healing confidence is below the auto-heal threshold."""
