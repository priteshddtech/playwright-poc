from __future__ import annotations

import re


class PiiMasker:
    """Mask sensitive values before sending content to an LLM."""

    DEFAULT_PATTERNS: list[tuple[str, str]] = [
        (r"(?i)(password|passwd|pwd)\s*[:=]\s*[^\s\"']+", r"\1=***"),
        (r"(?i)(api[_-]?key|token|jwt|secret)\s*[:=]\s*[^\s\"']+", r"\1=***"),
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL_REDACTED]"),
        (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN_REDACTED]"),
        (r"\b(?:\d[ -]*?){13,16}\b", "[CARD_REDACTED]"),
        (r"type=[\"']password[\"'][^>]*value=[\"'][^\"']*[\"']", "type=\"password\" value=\"***\""),
    ]

    def __init__(self, extra_patterns: list[tuple[str, str]] | None = None) -> None:
        self._patterns = list(self.DEFAULT_PATTERNS)
        if extra_patterns:
            self._patterns.extend(extra_patterns)

    def mask(self, text: str) -> str:
        result = text
        for pattern, replacement in self._patterns:
            result = re.sub(pattern, replacement, result)
        return result
