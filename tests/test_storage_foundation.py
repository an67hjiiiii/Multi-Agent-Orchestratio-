from __future__ import annotations

import pytest

from app.storage.sqlite_store import SYSTEM_TABLES, SQLiteMetadataStore
from app.storage.vector_store import InMemoryVectorStore, VectorRecord


def test_sqlite_creates_system_metadata_boundary_and_round_trips(tmp_path):
    path = tmp_path / "metadata.sqlite3"
    store = SQLiteMetadataStore(path)
    try:
        tables = {
            row[0]
            for row in store.connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        assert set(SYSTEM_TABLES).issubset(tables)

        stored = store.put("runs", "run-1", {"status": "COMPLETE", "tags": ["m0"]})
        assert stored["payload"] == {"status": "COMPLETE", "tags": ["m0"]}
        assert store.get("runs", "run-1") == stored["payload"]
        assert store.list_records("runs")[0]["id"] == "run-1"
    finally:
        store.close()


def test_sqlite_transaction_rolls_back_as_one_unit(tmp_path):
    store = SQLiteMetadataStore(tmp_path / "metadata.sqlite3")
    try:
        with pytest.raises(RuntimeError):
            with store.transaction():
                store.put("events", "event-1", {"kind": "started"})
                store.put("events", "event-2", {"kind": "failed"})
                raise RuntimeError("abort")
        assert store.get("events", "event-1") is None
        assert store.get("events", "event-2") is None
    finally:
        store.close()


def test_memory_vector_store_is_deterministic_and_keeps_payloads():
    store = InMemoryVectorStore(vector_size=2)
    store.upsert(
        [
            VectorRecord("a", (1, 0), {"source_id": "s-a"}),
            VectorRecord("b", (0, 1), {"source_id": "s-b"}),
        ]
    )
    matches = store.search((0.9, 0.1), limit=2)
    assert [match.id for match in matches] == ["a", "b"]
    assert matches[0].payload == {"source_id": "s-a"}
    store.delete(["a"])
    assert store.count() == 1


def test_metadata_table_and_vector_dimensions_are_validated(tmp_path):
    store = SQLiteMetadataStore(tmp_path / "metadata.sqlite3")
    try:
        with pytest.raises(ValueError, match="Unsupported metadata table"):
            store.put("users", "u-1", {})
    finally:
        store.close()

    vectors = InMemoryVectorStore(vector_size=2)
    with pytest.raises(ValueError, match="expected 2"):
        vectors.upsert([VectorRecord("bad", (1, 2, 3))])
