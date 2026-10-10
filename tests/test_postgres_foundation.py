from __future__ import annotations

import pytest
from sqlalchemy import ForeignKeyConstraint
from app.storage.postgres.base import Base
from app.storage.postgres.config import (
    PostgresConfigurationError,
    database_url_from_env,
)
from app.storage.postgres.models import (
    KnowledgeChunkRecord,
    KnowledgeSourceRecord,
    UserRecord,
)


def test_database_url_requires_explicit_postgres_driver() -> None:
    with pytest.raises(PostgresConfigurationError, match="must be set"):
        database_url_from_env({})

    with pytest.raises(PostgresConfigurationError, match=r"postgresql\+psycopg"):
        database_url_from_env({"DATABASE_URL": "sqlite:///metadata.sqlite3"})


def test_database_url_accepts_explicit_postgresql_psycopg() -> None:
    url = database_url_from_env(
        {"DATABASE_URL": "postgresql+psycopg://localhost/cap1_ai"}
    )

    assert url.drivername == "postgresql+psycopg"
    assert url.database == "cap1_ai"


def test_foundation_models_match_identity_and_source_scope() -> None:
    assert set(Base.metadata.tables) == {
        "users",
        "knowledge_sources",
        "knowledge_chunks",
    }
    assert UserRecord.__table__.c.password_hash.nullable is False
    assert KnowledgeSourceRecord.__table__.c.owner_user_id.nullable is False

    source_foreign_keys = [
        fk
        for constraint in KnowledgeSourceRecord.__table__.constraints
        if isinstance(constraint, ForeignKeyConstraint)
        for fk in constraint.elements
    ]
    chunk_foreign_keys = [
        fk
        for constraint in KnowledgeChunkRecord.__table__.constraints
        if isinstance(constraint, ForeignKeyConstraint)
        for fk in constraint.elements
    ]
    assert [(fk.target_fullname, fk.ondelete) for fk in source_foreign_keys] == [
        ("users.user_id", "CASCADE")
    ]
    assert [(fk.target_fullname, fk.ondelete) for fk in chunk_foreign_keys] == [
        ("knowledge_sources.source_id", "CASCADE")
    ]
