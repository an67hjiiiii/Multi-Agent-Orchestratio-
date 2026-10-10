# PostgreSQL schema foundation

The Sprint 1 PostgreSQL foundation defines database models and Alembic
migrations for users, knowledge sources, and knowledge chunks. An additive
migration adds owner-scoped conversations, ordered messages, and runs. This is
schema foundation only: product runtime stores continue to use their existing
last-known-good persistence until a separately approved runtime-wiring task.

PostgreSQL configuration is read from `DATABASE_URL` and requires the
`postgresql+psycopg` driver. There is no default database URL or silent
SQLite fallback. Apply the schema only to an explicitly prepared local test
database with `alembic upgrade head`.

User email and username uniqueness is enforced on normalized values, matching
the current trim-and-lowercase authentication contract. Knowledge chunks
require source, embedding, and indexing provenance. Conversation records are
owner-scoped; messages have per-conversation sequence numbers; and message/run
links must refer to the same conversation. Runs linked to conversations must
have the same owner. Standalone owner-scoped runs are representable.

Revisions `20261010_01` and `20261010_02` create the identity/source/chunk and
conversation/message/run schemas respectively. These migrations do not copy
data from existing stores, change runtime storage, or introduce citation,
trace, settings, vector, or PDF capabilities.

Focused schema and migration contract tests are in
`tests/test_postgres_foundation.py`. They do not execute migrations against a
live PostgreSQL instance.
