from __future__ import annotations

import re


class DomPruner:
    """Reduce HTML size while keeping interactive and semantic elements."""

    _INTERACTIVE_TAGS = re.compile(
        r"<(button|input|select|textarea|a|form|label|option)[^>]*>",
        re.IGNORECASE,
    )
    _HEADING_TAGS = re.compile(r"<h[1-6][^>]*>.*?</h[1-6]>", re.IGNORECASE | re.DOTALL)

    def __init__(self, max_bytes: int = 100_000) -> None:
        self._max_bytes = max_bytes

    def prune(self, html: str, failed_locator: str = "") -> str:
        if len(html.encode("utf-8")) <= self._max_bytes:
            return html

        chunks: list[str] = []
        for pattern in (self._INTERACTIVE_TAGS, self._HEADING_TAGS):
            chunks.extend(m.group(0) for m in pattern.finditer(html))

        if failed_locator:
            idx = html.find(failed_locator.replace("#", "id=\"").replace("#", ""))
            if idx >= 0:
                start = max(0, idx - 2000)
                end = min(len(html), idx + 2000)
                chunks.append(html[start:end])

        if not chunks:
            chunks.append(html[: self._max_bytes])

        combined = "\n".join(dict.fromkeys(chunks))
        encoded = combined.encode("utf-8")
        if len(encoded) > self._max_bytes:
            combined = encoded[: self._max_bytes].decode("utf-8", errors="ignore")
        return combined
