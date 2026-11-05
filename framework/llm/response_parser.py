from __future__ import annotations

import json
import re
from typing import Any

from framework.models.domain import HealingMethod, LocatorCandidate, LocatorDefinition, LocatorStrategy


class ResponseParser:
    def parse(self, raw: str) -> LocatorCandidate | None:
        payload = self._extract_json(raw)
        if not payload:
            return None

        strategy_raw = str(payload.get("strategy", "css")).lower()
        strategy = self._map_strategy(strategy_raw)
        value = str(payload.get("value", payload.get("candidate_locator", "")))
        role = payload.get("role")
        name = payload.get("name")
        confidence = float(payload.get("confidence", 0))
        reason = str(payload.get("reason", ""))
        frame_name = payload.get("frame_name")
        frame_url = payload.get("frame_url")

        if strategy == LocatorStrategy.ROLE:
            definition = LocatorDefinition(
                strategy=strategy,
                value=value or f"role:{role}:{name}",
                role=str(role) if role else "button",
                name=str(name) if name else None,
                frame_name=str(frame_name) if frame_name else None,
                frame_url=str(frame_url) if frame_url else None,
            )
        else:
            definition = LocatorDefinition(
                strategy=strategy,
                value=value,
                frame_name=str(frame_name) if frame_name else None,
                frame_url=str(frame_url) if frame_url else None,
            )

        return LocatorCandidate(
            definition=definition,
            method=HealingMethod.LLM,
            llm_confidence=confidence,
            reason=reason,
        )

    @staticmethod
    def _map_strategy(raw: str) -> LocatorStrategy:
        mapping = {
            "css": LocatorStrategy.CSS,
            "role": LocatorStrategy.ROLE,
            "text": LocatorStrategy.TEXT,
            "label": LocatorStrategy.LABEL,
            "placeholder": LocatorStrategy.PLACEHOLDER,
            "test_id": LocatorStrategy.TEST_ID,
        }
        return mapping.get(raw, LocatorStrategy.CSS)

    @staticmethod
    def _extract_json(raw: str) -> dict[str, Any] | None:
        raw = raw.strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not match:
                return None
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
