# PostgreSQL schema foundation

This Sprint 1 foundation defines PostgreSQL models for users, knowledge
sources, and knowledge chunks, plus the initial Alembic migration. It does not
change runtime storage behavior; the existing local stores remain the
last-known-good path until a separately approved runtime-wiring task.

PostgreSQL configuration is read from `DATABASE_URL` and requires the
`postgresql+psycopg` driver. There is no default database URL or silent
SQLite fallback. Apply the schema only to an explicitly prepared local test
database with `alembic upgrade head`.
