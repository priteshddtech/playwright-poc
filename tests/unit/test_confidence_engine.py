from framework.config.settings import Settings
from framework.healing.confidence_engine import ConfidenceEngine
from framework.models.domain import (
    ActionType,
    ElementIntent,
    HealingMethod,
    LocatorCandidate,
    LocatorDefinition,
    LocatorStrategy,
)


class _FakeLocator:
    def __init__(self, count: int, visible: bool = True, enabled: bool = True) -> None:
        self._count = count
        self._visible = visible
        self._enabled = enabled

    def count(self) -> int:
        return self._count

    def is_visible(self) -> bool:
        return self._visible

    def is_enabled(self) -> bool:
        return self._enabled


class _FakePage:
    pass


def test_confidence_high_for_unique_visible_match(monkeypatch) -> None:
    engine = ConfidenceEngine(Settings())
    intent = ElementIntent(
        element_key="submit",
        description="Submit button for employee registration form",
        locator="#submit",
        action=ActionType.CLICK,
    )
    candidate = LocatorCandidate(
        definition=LocatorDefinition(
            strategy=LocatorStrategy.ROLE,
            value="role:button:Submit",
            role="button",
            name="Submit",
        ),
        method=HealingMethod.HEURISTIC,
        reason="Submit role",
    )

    monkeypatch.setattr(
        "framework.healing.confidence_engine.LocatorResolver.resolve",
        lambda page, definition: _FakeLocator(1),
    )

    result = engine.validate(_FakePage(), intent, candidate, [])
    assert result.match_count == 1
    assert result.confidence >= 80.0
