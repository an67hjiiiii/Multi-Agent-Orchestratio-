from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


SYSTEM_TABLES = (
    "workspaces",
    "sources",
    "conversations",
    "messages",
    "runs",
    "tasks",
    "context_packets",
    "claims",
    "events",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class SQLiteMetadataStore:
    """Small transactional boundary for local system metadata.

    Records are intentionally opaque JSON payloads.  The storage foundation
    owns identity and timestamps; feature slices own the meaning of payloads.
    This prevents the foundation from inventing business data or coupling the
    current file-backed M0 stores to a future schema migration.
    """

    def __init__(self, path: str | Path = "storage/metadata.sqlite3") -> None:
        self.path = Path(path)
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(self.path), check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.initialize()

    def initialize(self) -> None:
        """Create only additive, generic system-metadata tables."""
        statements = [
            """
            CREATE TABLE IF NOT EXISTS storage_schema (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """,
        ]
        for table in SYSTEM_TABLES:
            statements.append(
                f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            statements.append(
                f"CREATE INDEX IF NOT EXISTS ix_{table}_updated_at ON {table}(updated_at)"
            )
        with self.transaction():
            for statement in statements:
                self.connection.execute(statement)
            self.connection.execute(
                "INSERT OR IGNORE INTO storage_schema(key, value) VALUES (?, ?)",
                ("version", "1"),
            )

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Run a group of writes atomically, including on an exception.

        SQLite does not support nested ``BEGIN`` statements.  Reusing an
        already-open transaction makes this helper safe for methods called by
        a larger transaction while preserving the caller's commit boundary.
        """
        outer = self.connection.in_transaction
        if not outer:
            self.connection.execute("BEGIN IMMEDIATE")
        try:
            yield self.connection
        except Exception:
            if not outer:
                self.connection.rollback()
            raise
        else:
            if not outer:
                self.connection.commit()

    @staticmethod
    def _validate_table(table: str) -> str:
        if table not in SYSTEM_TABLES:
            allowed = ", ".join(SYSTEM_TABLES)
            raise ValueError(f"Unsupported metadata table {table!r}; allowed: {allowed}")
        return table

    @staticmethod
    def _validate_id(record_id: str) -> str:
        if not isinstance(record_id, str) or not record_id.strip():
            raise ValueError("record_id must be a non-empty string")
        return record_id

    def put(
        self,
        table: str,
        record_id: str,
        payload: dict,
        *,
        created_at: str | None = None,
        updated_at: str | None = None,
    ) -> dict:
        table = self._validate_table(table)
        record_id = self._validate_id(record_id)
        if not isinstance(payload, dict):
            raise TypeError("payload must be a dictionary")
        now = _now()
        updated = updated_at or now
        created = created_at or now
        existing = self.connection.execute(
            f"SELECT created_at FROM {table} WHERE id = ?", (record_id,)
        ).fetchone()
        if existing:
            created = existing["created_at"]
        with self.transaction():
            self.connection.execute(
                f"""
                INSERT INTO {table}(id, payload_json, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at
                """,
                (
                    record_id,
                    json.dumps(payload, ensure_ascii=False, sort_keys=True),
                    created,
                    updated,
                ),
            )
        return self.get_record(table, record_id)  # type: ignore[return-value]

    # ``upsert`` is a deliberately explicit alias for callers that use SQL
    # terminology; both names share exactly the same behavior.
    upsert = put

    def get_record(self, table: str, record_id: str) -> dict | None:
        table = self._validate_table(table)
        record_id = self._validate_id(record_id)
        row = self.connection.execute(
            f"SELECT id, payload_json, created_at, updated_at FROM {table} WHERE id = ?",
            (record_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "payload": json.loads(row["payload_json"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def get(self, table: str, record_id: str) -> dict | None:
        record = self.get_record(table, record_id)
        return None if record is None else record["payload"]

    def list_records(
        self, table: str, *, limit: int = 100, offset: int = 0
    ) -> list[dict]:
        table = self._validate_table(table)
        if limit < 1 or offset < 0:
            raise ValueError("limit must be positive and offset must not be negative")
        rows = self.connection.execute(
            f"""
            SELECT id, payload_json, created_at, updated_at
            FROM {table}
            ORDER BY updated_at DESC, id ASC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
        return [
            {
                "id": row["id"],
                "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]

    def list(self, table: str, limit: int = 100) -> list[dict]:
        """Compatibility spelling for callers that use the existing stores."""
        return self.list_records(table, limit=limit)

    def delete(self, table: str, record_id: str) -> bool:
        table = self._validate_table(table)
        record_id = self._validate_id(record_id)
        with self.transaction():
            cursor = self.connection.execute(
                f"DELETE FROM {table} WHERE id = ?", (record_id,)
            )
        return cursor.rowcount > 0

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "SQLiteMetadataStore":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()


SQLiteStore = SQLiteMetadataStore
