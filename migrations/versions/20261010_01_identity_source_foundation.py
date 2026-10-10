"""Create PostgreSQL identity and source foundation.

Revision ID: 20261010_01
Revises:
Create Date: 2026-10-10
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20261010_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column(
            "status", sa.String(length=32), server_default="ACTIVE", nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "email IS NOT NULL OR username IS NOT NULL",
            name="ck_users_login_identity",
        ),
        sa.CheckConstraint(
            "email IS NULL OR btrim(email) <> ''",
            name="ck_users_email_nonempty",
        ),
        sa.CheckConstraint(
            "username IS NULL OR btrim(username) <> ''",
            name="ck_users_username_nonempty",
        ),
        sa.CheckConstraint("role IN ('USER', 'ADMIN')", name="ck_users_role"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index(
        "uq_users_email_normalized",
        "users",
        [sa.text("lower(btrim(email))")],
        unique=True,
        postgresql_where=sa.text("email IS NOT NULL"),
    )
    op.create_index(
        "uq_users_username_normalized",
        "users",
        [sa.text("lower(btrim(username))")],
        unique=True,
        postgresql_where=sa.text("username IS NOT NULL"),
    )
    op.create_table(
        "knowledge_sources",
        sa.Column("source_id", sa.String(length=128), nullable=False),
        sa.Column("owner_user_id", sa.String(length=64), nullable=False),
        sa.Column("source_name", sa.String(length=512), nullable=False),
        sa.Column(
            "status", sa.String(length=32), server_default="PROCESSING", nullable=False
        ),
        sa.Column("file_ref", sa.Text(), nullable=True),
        sa.Column("display_metadata", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('PROCESSING', 'READY', 'FAILED')",
            name="ck_knowledge_sources_lifecycle",
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"], ["users.user_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("source_id"),
    )
    op.create_index(
        "ix_knowledge_sources_owner_user_id",
        "knowledge_sources",
        ["owner_user_id"],
    )
    op.create_index(
        "ix_knowledge_sources_owner_status",
        "knowledge_sources",
        ["owner_user_id", "status"],
    )
    op.create_table(
        "knowledge_chunks",
        sa.Column("chunk_id", sa.String(length=160), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=False),
        sa.Column("source_version", sa.String(length=128), nullable=False),
        sa.Column("source_hash", sa.String(length=128), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("location", sa.JSON(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("content_ref", sa.String(length=1024), nullable=True),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("indexing_version", sa.String(length=128), nullable=False),
        sa.Column("embedding_version", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "chunk_index >= 0", name="ck_knowledge_chunks_index"
        ),
        sa.CheckConstraint(
            "length(btrim(source_version)) > 0",
            name="ck_knowledge_chunks_source_version_nonempty",
        ),
        sa.CheckConstraint(
            "length(btrim(source_hash)) > 0",
            name="ck_knowledge_chunks_source_hash_nonempty",
        ),
        sa.CheckConstraint(
            "length(btrim(embedding_version)) > 0",
            name="ck_knowledge_chunks_embedding_version_nonempty",
        ),
        sa.CheckConstraint(
            "length(btrim(indexing_version)) > 0",
            name="ck_knowledge_chunks_indexing_version_nonempty",
        ),
        sa.CheckConstraint(
            "CASE WHEN json_typeof(provenance) = 'object' "
            "THEN provenance::jsonb <> '{}'::jsonb ELSE FALSE END",
            name="ck_knowledge_chunks_provenance_nonempty_object",
        ),
        sa.CheckConstraint(
            "content IS NOT NULL OR content_ref IS NOT NULL",
            name="ck_knowledge_chunks_content_reference",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"], ["knowledge_sources.source_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("chunk_id"),
        sa.UniqueConstraint(
            "source_id", "chunk_index", name="uq_knowledge_chunks_source_index"
        ),
    )
    op.create_index(
        "ix_knowledge_chunks_source_id", "knowledge_chunks", ["source_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_knowledge_chunks_source_id", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
    op.drop_index(
        "ix_knowledge_sources_owner_status", table_name="knowledge_sources"
    )
    op.drop_index(
        "ix_knowledge_sources_owner_user_id", table_name="knowledge_sources"
    )
    op.drop_table("knowledge_sources")
    op.drop_index("uq_users_username_normalized", table_name="users")
    op.drop_index("uq_users_email_normalized", table_name="users")
    op.drop_table("users")
