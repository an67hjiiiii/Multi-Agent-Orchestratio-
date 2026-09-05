# Local storage foundation

This slice establishes local storage boundaries without changing the current
retrieval pipeline. `RunStore` and `SourceStore` remain JSON-backed and are
still valid compatibility adapters for the M0 candidate.

## SQLite metadata

`app.storage.sqlite_store.SQLiteMetadataStore` owns a local SQLite file and
creates the generic system-metadata tables named in the research plan:

`workspaces`, `sources`, `conversations`, `messages`, `runs`, `tasks`,
`context_packets`, `claims`, and `events`.

Each table stores an opaque JSON payload plus an ID and UTC timestamps. The
foundation does not define business fields. Use `put`/`upsert`, `get`,
`get_record`, `list_records`, and `delete`. Use `transaction()` when multiple
metadata writes must commit or roll back together.

```python
from app.storage.sqlite_store import SQLiteMetadataStore

with SQLiteMetadataStore("storage/metadata.sqlite3") as store:
    with store.transaction():
        store.put("runs", "run-123", {"status": "COMPLETE"})
        store.put("events", "event-123", {"kind": "run.completed"})
```

The default path and vector settings are recorded in
`config/storage/defaults.json`. Environment overrides are available through
`StorageConfig.from_env()` (`STORAGE_SQLITE_PATH`, `VECTOR_BACKEND`,
`QDRANT_PATH`, `QDRANT_COLLECTION`, and `VECTOR_SIZE`).

## Vector boundary

`VectorRecord` and `VectorMatch` define the backend-neutral contract.
`InMemoryVectorStore` is a deterministic, dependency-free fake for focused
unit tests. `QdrantVectorStore` is an optional lazy adapter: it imports
`qdrant-client` only when instantiated and creates a local collection on
demand. Qdrant is therefore adapter-ready, not an active runtime dependency in
this candidate. No embedding generation or retrieval behavior is introduced
by this slice.

## Scope and verification

Focused tests are in `tests/test_storage_foundation.py`. They cover schema
creation, JSON round trips, transaction rollback, vector ordering/payload
preservation, and input validation. Existing source/run-store and pipeline
tests remain unchanged.
