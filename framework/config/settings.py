from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    application_id: str = "enterprise_app"
    environment: str = "local"

    artifacts_dir: Path = Path("artifacts")
    sqlite_path: Path = Path("artifacts/locator_kb.db")

    action_timeout_ms: int = 5000
    max_heal_attempts: int = 3
    max_candidates: int = 10

    confidence_auto_heal: float = 95.0
    confidence_warn: float = 80.0

    weight_semantic: float = 0.25
    weight_accessibility: float = 0.20
    weight_dom_context: float = 0.20
    weight_uniqueness: float = 0.15
    weight_visibility: float = 0.10
    weight_history: float = 0.10

    dom_prune_max_bytes: int = 100_000

    fuzzy_match_enabled: bool = True
    fuzzy_match_threshold: float = 0.85

    llm_mode: Literal["openai", "mock"] = "mock"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    capture_console_logs: bool = True
    log_healing_summary_console: bool = False


def get_settings() -> Settings:
    return Settings()
