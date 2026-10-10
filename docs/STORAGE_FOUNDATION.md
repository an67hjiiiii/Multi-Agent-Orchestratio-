# PostgreSQL product persistence

PostgreSQL is the authoritative store for product users, sessions, private
sources and chunks, conversations and ordered messages, and runs. Runtime
stores preserve the existing auth, ownership, retrieval, and run contracts.
JSON stores are available only when `APP_STORAGE_BACKEND=file` is explicitly
selected for isolated test/demo use; the product default is PostgreSQL and
does not silently fall back when configuration is missing.

PostgreSQL configuration is read from `DATABASE_URL` and requires the
`postgresql+psycopg` driver. There is no default database URL or silent
SQLite fallback. Apply the schema only to an explicitly prepared local test
database with `alembic upgrade head`.

User email and username uniqueness is enforced on normalized values, matching
the current trim-and-lowercase authentication contract. Session tokens are
stored only as SHA-256 hashes with expiry and revocation timestamps. Source and
chunk reads are owner-scoped; source identity is namespaced deterministically
per owner. Conversation records are owner-scoped; messages have per-conversation
sequence numbers; and message/run links refer to the same conversation. Runs
linked to conversations must have the same owner.

Revisions `20261010_01` and `20261010_02` create identity/source/chunk and
conversation/message/run schemas. Revision `20261010_03` adds session
persistence. These migrations do not copy existing JSON data into PostgreSQL.

Schema/migration contract tests are in `tests/test_postgres_foundation.py`;
runtime store tests are in `tests/test_postgres_runtime_stores.py`. The
PostgreSQL 16 migration and live API persistence/reconnect gate is exercised by
`tests/test_postgres_product_runtime.py` against a dedicated database.
