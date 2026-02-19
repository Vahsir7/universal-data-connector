"""SQLite database singleton with thread-safe access.

Creates the data directory and schema on first use.  All tables
(api_keys, webhook_events, llm_provider_keys) are initialised
automatically via CREATE TABLE IF NOT EXISTS.
"""

import sqlite3
import threading
from pathlib import Path
from typing import Any, Iterable, List, Optional, Sequence

from app.config import settings


class DbService:
    """Lightweight SQLite wrapper with per-call connections and a global lock."""
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._db_path = Path(settings.APP_DB_PATH)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._lock, self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS api_keys (
                    key_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    key_hash TEXT NOT NULL,
                    key_value TEXT,
                    source TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    revoked INTEGER NOT NULL DEFAULT 0,
                    last_used_at TEXT
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS webhook_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    received_at TEXT NOT NULL,
                    source TEXT,
                    event_type TEXT,
                    payload TEXT
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS llm_provider_keys (
                    key_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT,
                    key_hash TEXT NOT NULL,
                    key_value TEXT NOT NULL,
                    source TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    revoked INTEGER NOT NULL DEFAULT 0,
                    last_used_at TEXT
                )
                """
            )
            try:
                cursor.execute("ALTER TABLE llm_provider_keys ADD COLUMN model TEXT")
            except sqlite3.OperationalError:
                pass
            connection.commit()

    def execute(self, sql: str, params: Optional[Sequence[Any]] = None) -> int:
        with self._lock, self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(sql, params or [])
            connection.commit()
            return cursor.rowcount

    def executemany(self, sql: str, params: Iterable[Sequence[Any]]) -> int:
        with self._lock, self._connect() as connection:
            cursor = connection.cursor()
            cursor.executemany(sql, list(params))
            connection.commit()
            return cursor.rowcount

    def fetchone(self, sql: str, params: Optional[Sequence[Any]] = None) -> Optional[sqlite3.Row]:
        with self._lock, self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(sql, params or [])
            return cursor.fetchone()

    def fetchall(self, sql: str, params: Optional[Sequence[Any]] = None) -> List[sqlite3.Row]:
        with self._lock, self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(sql, params or [])
            return cursor.fetchall()


_db_service_singleton = DbService()


def get_db_service() -> DbService:
    return _db_service_singleton
