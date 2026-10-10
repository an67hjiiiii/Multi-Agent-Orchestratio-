"""Opt-in PostgreSQL schema foundation; product stores are not wired to it."""

from app.storage.postgres.base import Base
from app.storage.postgres.config import (
    PostgresConfigurationError,
    create_postgres_engine,
    create_session_factory,
    database_url_from_env,
)
from app.storage.postgres.models import (
    KnowledgeChunkRecord,
    KnowledgeSourceRecord,
    UserRecord,
)

__all__ = [
    "Base",
    "KnowledgeChunkRecord",
    "KnowledgeSourceRecord",
    "PostgresConfigurationError",
    "UserRecord",
    "create_postgres_engine",
    "create_session_factory",
    "database_url_from_env",
]
