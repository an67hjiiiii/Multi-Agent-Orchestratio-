"""Opt-in PostgreSQL schema foundation; product stores are not wired to it."""

from app.storage.postgres.base import Base
from app.storage.postgres.config import (
    PostgresConfigurationError,
    create_postgres_engine,
    create_session_factory,
    database_url_from_env,
)
from app.storage.postgres.models import (
    ConversationMessageRecord,
    ConversationRecord,
    KnowledgeChunkRecord,
    KnowledgeSourceRecord,
    RunRecord,
    UserRecord,
)

__all__ = [
    "Base",
    "ConversationMessageRecord",
    "ConversationRecord",
    "KnowledgeChunkRecord",
    "KnowledgeSourceRecord",
    "PostgresConfigurationError",
    "RunRecord",
    "UserRecord",
    "create_postgres_engine",
    "create_session_factory",
    "database_url_from_env",
]
