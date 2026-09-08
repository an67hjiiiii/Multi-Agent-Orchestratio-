# Local storage foundation

This slice establishes local storage boundaries and the opt-in Knowledge
Engine V3 retrieval modes. `RunStore` and `SourceStore` remain JSON-backed and
are still valid compatibility adapters for the M0 candidate.

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
`StorageConfig.from_env()` (`STORAGE_SQLITE_PATH`, `RETRIEVAL_MODE`,
`VECTOR_BACKEND`, `QDRANT_PATH`, `QDRANT_COLLECTION`, `VECTOR_SIZE`,
`EMBEDDING_PROVIDER`, and `LOCAL_EMBEDDING_MODEL`).

## Vector boundary

`VectorRecord` and `VectorMatch` define the backend-neutral contract.
`InMemoryVectorStore` is a deterministic, dependency-free store for focused
development checks. `QdrantVectorStore` is an optional lazy adapter: it imports
`qdrant-client` only when instantiated and creates a local collection on
demand. `LEXICAL`, `VECTOR`, and `HYBRID` are explicit modes; a requested
vector mode reports `UNAVAILABLE` rather than silently changing the experiment
to lexical retrieval. The default remains `LEXICAL`.

The default hash embedder is deterministic/offline. `OllamaEmbedder` is an
opt-in local-only adapter for a configured embedding model; it never permits a
remote base URL. PDF ingestion uses optional `pypdf` text extraction and
returns an explicit no-text state for scanned-image documents.

## Scope and verification

Focused tests are in `tests/test_storage_foundation.py`. They cover schema
creation, JSON round trips, transaction rollback, vector ordering/payload
preservation, and input validation. Existing source/run-store and pipeline
tests remain unchanged.
