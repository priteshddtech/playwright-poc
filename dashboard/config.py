from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class DashboardSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    artifacts_dir: Path = Path("artifacts")
    audit_log_path: Path | None = None
    sqlite_path: Path | None = None

    def resolved_artifacts_dir(self) -> Path:
        return self.artifacts_dir.expanduser().resolve()

    def resolved_audit_log_path(self) -> Path:
        if self.audit_log_path is not None:
            return self.audit_log_path.expanduser().resolve()
        return self.resolved_artifacts_dir() / "logs" / "healing_audit.jsonl"

    def resolved_sqlite_path(self) -> Path:
        if self.sqlite_path is not None:
            return self.sqlite_path.expanduser().resolve()
        return self.resolved_artifacts_dir() / "locator_kb.db"


@lru_cache
def get_dashboard_settings() -> DashboardSettings:
    return DashboardSettings()
