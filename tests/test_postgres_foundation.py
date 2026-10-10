from pathlib import Path

import pytest
from sqlalchemy import CheckConstraint, ForeignKeyConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import configure_mappers
from sqlalchemy.schema import CreateTable

from app.storage.postgres.base import Base
from app.storage.postgres.config import (
    PostgresConfigurationError,
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
        "conversations",
        "conversation_messages",
        "runs",
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


def test_user_indexes_enforce_auth_trim_and_lower_normalization() -> None:
    indexes = {index.name: index for index in UserRecord.__table__.indexes}

    for field_name in ("email", "username"):
        index = indexes[f"uq_users_{field_name}_normalized"]
        expression = str(
            index.expressions[0].compile(dialect=postgresql.dialect())
        )
        predicate = str(
            index.dialect_options["postgresql"]["where"].compile(
                dialect=postgresql.dialect()
            )
        )
        assert index.unique is True
        assert expression == f"lower(btrim({field_name}))"
        assert predicate == f"{field_name} IS NOT NULL"

    check_names = {constraint.name for constraint in UserRecord.__table__.constraints}
    assert "ck_users_email_nonempty" in check_names
    assert "ck_users_username_nonempty" in check_names


def test_chunks_require_version_hash_embedding_and_nonempty_provenance() -> None:
    columns = KnowledgeChunkRecord.__table__.c
    for field_name in (
        "source_version",
        "source_hash",
        "embedding_version",
        "indexing_version",
    ):
        assert columns[field_name].nullable is False

    check_constraints = {
        constraint.name: str(constraint.sqltext)
        for constraint in KnowledgeChunkRecord.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert "ck_knowledge_chunks_source_version_nonempty" in check_constraints
    assert "ck_knowledge_chunks_source_hash_nonempty" in check_constraints
    assert "ck_knowledge_chunks_embedding_version_nonempty" in check_constraints
    assert "ck_knowledge_chunks_indexing_version_nonempty" in check_constraints
    assert "ck_knowledge_chunks_provenance_nonempty_object" in check_constraints
    assert "json_typeof(provenance) = 'object'" in check_constraints[
        "ck_knowledge_chunks_provenance_nonempty_object"
    ]
    assert "provenance::jsonb <> '{}'::jsonb" in check_constraints[
        "ck_knowledge_chunks_provenance_nonempty_object"
    ]

    postgres_ddl = str(
        CreateTable(KnowledgeChunkRecord.__table__).compile(
            dialect=postgresql.dialect()
        )
    )
    assert "source_version VARCHAR(128) NOT NULL" in postgres_ddl
    assert "source_hash VARCHAR(128) NOT NULL" in postgres_ddl
    assert "embedding_version VARCHAR(128) NOT NULL" in postgres_ddl
    assert "provenance::jsonb <> '{}'::jsonb" in postgres_ddl


def test_initial_migration_carries_the_model_contract() -> None:
    migration_path = (
        Path(__file__).parents[1]
        / "migrations"
        / "versions"
        / "20261010_01_identity_source_foundation.py"
    )
    migration = migration_path.read_text(encoding="utf-8")

    assert '"lower(btrim(email))"' in migration
    assert '"lower(btrim(username))"' in migration
    assert (
        'sa.Column("source_version", sa.String(length=128), nullable=False)'
        in migration
    )
    assert (
        'sa.Column("source_hash", sa.String(length=128), nullable=False)'
        in migration
    )
    assert (
        'sa.Column("embedding_version", sa.String(length=128), nullable=False)'
        in migration
    )
    assert "provenance::jsonb <> '{}'::jsonb" in migration


def test_conversation_run_models_preserve_owner_order_and_run_links() -> None:
    conversations = ConversationRecord.__table__
    messages = ConversationMessageRecord.__table__
    runs = RunRecord.__table__

    conversation_owner_fks = [
        fk
        for constraint in conversations.constraints
        if isinstance(constraint, ForeignKeyConstraint)
        for fk in constraint.elements
    ]
    assert [(fk.target_fullname, fk.ondelete) for fk in conversation_owner_fks] == [
        ("users.user_id", "CASCADE")
    ]
    assert conversations.c.owner_user_id.nullable is False
    assert "uq_conversations_id_owner" in {
        constraint.name for constraint in conversations.constraints
    }

    message_checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in messages.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert "sequence_number >= 0" in message_checks[
        "ck_conversation_messages_sequence"
    ]
    assert "role IN ('USER', 'ASSISTANT')" in message_checks[
        "ck_conversation_messages_role"
    ]
    assert "uq_conversation_messages_order" in {
        constraint.name for constraint in messages.constraints
    }

    message_run_fk = next(
        constraint
        for constraint in messages.constraints
        if isinstance(constraint, ForeignKeyConstraint)
        and constraint.name == "fk_conversation_messages_run_same_conversation"
    )
    assert [fk.target_fullname for fk in message_run_fk.elements] == [
        "runs.conversation_id",
        "runs.run_id",
    ]
    assert message_run_fk.ondelete == "RESTRICT"

    run_checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in runs.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert run_checks["ck_runs_conversation_requires_owner"] == (
        "conversation_id IS NULL OR owner_user_id IS NOT NULL"
    )
    run_owner_fk = next(
        constraint
        for constraint in runs.constraints
        if isinstance(constraint, ForeignKeyConstraint)
        and constraint.name == "fk_runs_conversation_owner"
    )
    assert [fk.target_fullname for fk in run_owner_fk.elements] == [
        "conversations.conversation_id",
        "conversations.owner_user_id",
    ]
    assert run_owner_fk.ondelete == "RESTRICT"
    run_user_fk = next(
        constraint
        for constraint in runs.constraints
        if isinstance(constraint, ForeignKeyConstraint)
        and constraint.name == "fk_runs_owner_user"
    )
    assert [fk.target_fullname for fk in run_user_fk.elements] == ["users.user_id"]
    assert run_user_fk.ondelete == "RESTRICT"
    assert runs.c.owner_user_id.nullable is True
    assert runs.c.tasks.nullable is False
    assert runs.c.events.nullable is False
    assert runs.c.effective_config.nullable is False
    assert runs.c.extra_data.nullable is False

    run_ddl = str(CreateTable(runs).compile(dialect=postgresql.dialect()))
    message_ddl = str(CreateTable(messages).compile(dialect=postgresql.dialect()))
    assert "FOREIGN KEY(conversation_id, owner_user_id)" in run_ddl
    assert "REFERENCES conversations (conversation_id, owner_user_id)" in run_ddl
    assert "FOREIGN KEY(conversation_id, run_id)" in message_ddl
    assert "REFERENCES runs (conversation_id, run_id)" in message_ddl


def test_conversation_run_orm_relationships_and_migration_are_registered() -> None:
    configure_mappers()
    assert ConversationRecord.messages.property.back_populates == "conversation"
    assert [column.key for column in ConversationRecord.messages.property.order_by] == [
        "sequence_number"
    ]
    assert ConversationRecord.runs.property.back_populates == "conversation"
    assert RunRecord.conversation.property.back_populates == "runs"
    assert UserRecord.runs.property.passive_deletes == "all"
    assert ConversationRecord.runs.property.passive_deletes == "all"

    migration_path = (
        Path(__file__).parents[1]
        / "migrations"
        / "versions"
        / "20261010_02_conversation_run_foundation.py"
    )
    migration = migration_path.read_text(encoding="utf-8")

    assert 'revision = "20261010_02"' in migration
    assert 'down_revision = "20261010_01"' in migration
    for table_name in ("conversations", "runs", "conversation_messages"):
        assert f'"{table_name}"' in migration
    assert "fk_runs_conversation_owner" in migration
    assert "fk_conversation_messages_run_same_conversation" in migration
    assert "uq_conversation_messages_order" in migration
