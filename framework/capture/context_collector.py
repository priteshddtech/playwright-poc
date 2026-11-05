from __future__ import annotations

import uuid
from pathlib import Path

from playwright.sync_api import Page

from framework.capture.dom_pruner import DomPruner
from framework.config.settings import Settings
from framework.knowledge.locator_repository import LocatorRepository
from framework.models.domain import ElementIntent, FailureContext, FrameInfo


class ContextCollector:
    def __init__(
        self,
        settings: Settings,
        repository: LocatorRepository,
        dom_pruner: DomPruner | None = None,
    ) -> None:
        self._settings = settings
        self._repository = repository
        self._dom_pruner = dom_pruner or DomPruner(settings.dom_prune_max_bytes)
        self._artifacts = settings.artifacts_dir
        self._artifacts.mkdir(parents=True, exist_ok=True)

    def collect(
        self,
        page: Page,
        intent: ElementIntent,
        application_id: str,
        page_key: str,
        error_message: str,
    ) -> FailureContext:
        run_id = uuid.uuid4().hex[:12]
        html_raw = page.content()
        failed_loc = intent.primary_locator.to_storage_string()
        html_pruned = self._dom_pruner.prune(html_raw, failed_loc)
        html_pruned = self._append_frame_html(page, html_pruned)

        html_path = self._artifacts / "html" / f"{run_id}.html"
        html_path.parent.mkdir(parents=True, exist_ok=True)
        html_path.write_text(html_pruned, encoding="utf-8")

        screenshot_path = self._artifacts / "screenshots" / f"{run_id}.png"
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(screenshot_path), full_page=True)

        try:
            a11y = page.accessibility.snapshot(interesting_only=True)
        except Exception:
            a11y = {}

        frames = [
            FrameInfo(name=frame.name or "", url=frame.url or "", index=i)
            for i, frame in enumerate(page.frames)
        ]

        console_logs: list[str] = []
        if self._settings.capture_console_logs:
            console_logs = list(getattr(page, "_healing_console_logs", []))

        history = self._repository.get_history(application_id, page_key, intent.element_key)

        return FailureContext(
            url=page.url,
            title=page.title(),
            html_pruned=html_pruned,
            html_snapshot_path=str(html_path),
            screenshot_path=str(screenshot_path),
            accessibility_tree=a11y,
            frames=frames,
            console_logs=console_logs,
            failed_locator=failed_loc,
            error_message=error_message,
            historical_locators=history,
        )

    def _append_frame_html(self, page: Page, html_pruned: str) -> str:
        chunks = [html_pruned]
        for frame in page.frames:
            if frame == page.main_frame:
                continue
            try:
                frame_html = self._dom_pruner.prune(frame.content())
            except Exception:
                continue
            label = frame.name or frame.url or "child-frame"
            chunks.append(f"\n<!-- iframe:{label} -->\n{frame_html}")
        combined = "\n".join(chunks)
        max_bytes = self._settings.dom_prune_max_bytes
        if len(combined.encode("utf-8")) > max_bytes:
            combined = combined.encode("utf-8")[:max_bytes].decode("utf-8", errors="ignore")
        return combined
