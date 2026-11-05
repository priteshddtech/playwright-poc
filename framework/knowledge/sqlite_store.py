from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path
from typing import Optional

from framework.knowledge.locator_repository import LocatorRepository
from framework.models.domain import HealingEventRecord, LocatorDefinition


class SQLiteLocatorRepository(LocatorRepository):
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS locator_memory (
                    id TEXT PRIMARY KEY,
                    application_id TEXT NOT NULL,
                    page_key TEXT NOT NULL,
                    logical_name TEXT NOT NULL,
                    current_locator TEXT NOT NULL,
                    confidence REAL,
                    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    success_count INTEGER DEFAULT 0,
                    UNIQUE(application_id, page_key, logical_name)
                );

                CREATE TABLE IF NOT EXISTS locator_history (
                    id TEXT PRIMARY KEY,
                    application_id TEXT NOT NULL,
                    page_key TEXT NOT NULL,
                    logical_name TEXT NOT NULL,
                    locator TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS healing_events (
                    id TEXT PRIMARY KEY,
                    execution_id TEXT NOT NULL,
                    element_key TEXT NOT NULL,
                    failed_locator TEXT NOT NULL,
                    healed_locator TEXT,
                    confidence REAL,
                    status TEXT NOT NULL,
                    healing_method TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

    def get_current(
        self, application_id: str, page_key: str, element_key: str
    ) -> Optional[LocatorDefinition]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT current_locator FROM locator_memory
                WHERE application_id = ? AND page_key = ? AND logical_name = ?
                """,
                (application_id, page_key, element_key),
            ).fetchone()
        if not row:
            return None
        return LocatorDefinition.from_storage_string(row["current_locator"])

    def get_history(
        self, application_id: str, page_key: str, element_key: str
    ) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT locator FROM locator_history
                WHERE application_id = ? AND page_key = ? AND logical_name = ?
                ORDER BY created_at DESC
                LIMIT 20
                """,
                (application_id, page_key, element_key),
            ).fetchall()
        seen: set[str] = set()
        result: list[str] = []
        for row in rows:
            loc = row["locator"]
            if loc not in seen:
                seen.add(loc)
                result.append(loc)
        return result

    def promote_locator(
        self,
        application_id: str,
        page_key: str,
        element_key: str,
        locator: LocatorDefinition,
        confidence: float,
    ) -> None:
        stored = locator.to_storage_string()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO locator_memory (
                    id, application_id, page_key, logical_name,
                    current_locator, confidence, success_count
                ) VALUES (?, ?, ?, ?, ?, ?, 1)
                ON CONFLICT(application_id, page_key, logical_name) DO UPDATE SET
                    current_locator = excluded.current_locator,
                    confidence = excluded.confidence,
                    last_used = CURRENT_TIMESTAMP,
                    success_count = success_count + 1
                """,
                (str(uuid.uuid4()), application_id, page_key, element_key, stored, confidence),
            )

    def append_history(
        self,
        application_id: str,
        page_key: str,
        element_key: str,
        locator: str,
        success: bool,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO locator_history (
                    id, application_id, page_key, logical_name, locator, success
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    application_id,
                    page_key,
                    element_key,
                    locator,
                    1 if success else 0,
                ),
            )

    def record_healing_event(self, event: HealingEventRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO healing_events (
                    id, execution_id, element_key, failed_locator,
                    healed_locator, confidence, status, healing_method, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    event.execution_id,
                    event.element_key,
                    event.failed_locator,
                    event.healed_locator,
                    event.confidence,
                    event.status,
                    event.healing_method,
                    event.created_at.isoformat(),
                ),
            )
