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

## PostgreSQL schema foundation

`app.storage.postgres` contains an opt-in SQLAlchemy 2 model base and the
initial Alembic schema for users, knowledge sources, and knowledge chunks.
PostgreSQL configuration is read only from `DATABASE_URL`, which must use the
`postgresql+psycopg` driver. There is no default URL and no SQLite fallback.
Email and username uniqueness is enforced by PostgreSQL on
`lower(btrim(value))`, matching the current auth store's trim-and-lowercase
normalization; null identifiers are allowed, but blank identifiers are not.

Each knowledge chunk stores non-empty `source_version`, `source_hash`,
`embedding_version`, and `indexing_version` values. Its `provenance` must be a
non-empty JSON object. These are database constraints as well as model fields,
so the contract does not depend only on callers validating input.

The additive conversation/run schema defines owner-scoped `conversations`,
ordered `conversation_messages`, and structured `runs`. Message ordering uses a
per-conversation sequence number. A message's optional `run_id` must refer to a
run from that same conversation. Runs attached to a conversation must carry
the same owner as the conversation; standalone runs may have an owner without
a conversation. Ownerless standalone records remain representable for
compatibility, and owner-scoped reads must continue to fail closed for them.
The run contract's `owner_id` maps to PostgreSQL's `owner_user_id`. Nested run
data such as tasks, results, events, metrics, effective configuration,
retrieval metadata, and additive fields has JSON columns so it remains
representable alongside indexed identity and status fields.

The migration is a schema foundation only. It does not copy data from the
existing JSON or SQLite stores, and the current API/runtime continues using
those stores as its last-known-good path. No application routes or services
open a PostgreSQL connection yet. The conversation/run migration is additive;
it does not replace or migrate the file-backed conversation or run stores.

To apply the schema to an explicitly prepared local PostgreSQL database, set
`DATABASE_URL` in the process environment and run `alembic upgrade head` from
the repository root. Do not run this against a database containing unrelated
or user data. Revision `20261010_01` creates users and knowledge-source
entities; revision `20261010_02` adds conversations, ordered messages, and
runs. Citation, trace, and settings tables remain for their later owning
tasks.

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

Focused tests are in `tests/test_storage_foundation.py` and
`tests/test_postgres_foundation.py`. They cover SQLite round trips and rollback,
vector ordering/payload preservation, PostgreSQL model constraints and
relationships, explicit database URL configuration, and migration contracts.
These checks do not execute a migration against a live database. Existing
source/run-store and pipeline paths remain unchanged.
