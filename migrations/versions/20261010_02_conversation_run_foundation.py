"""Create the conversation and run persistence foundation.

Revision ID: 20261010_02
Revises: 20261010_01
Create Date: 2026-10-10
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20261010_02"
down_revision = "20261010_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("conversation_id", sa.String(length=64), nullable=False),
        sa.Column("owner_user_id", sa.String(length=64), nullable=False),
        sa.Column(
            "schema_version",
            sa.String(length=32),
            server_default="conversation-v1",
            nullable=False,
        ),
        sa.Column(
            "title",
            sa.String(length=120),
            server_default="New conversation",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(btrim(title)) > 0", name="ck_conversations_title_nonempty"
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.user_id"],
            name="fk_conversations_owner_user",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("conversation_id"),
        sa.UniqueConstraint(
            "conversation_id", "owner_user_id", name="uq_conversations_id_owner"
        ),
    )
    op.create_index(
        "ix_conversations_owner_updated",
        "conversations",
        ["owner_user_id", "updated_at"],
    )

    op.create_table(
        "runs",
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("owner_user_id", sa.String(length=64), nullable=True),
        sa.Column("conversation_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("condition", sa.String(length=16), nullable=True),
        sa.Column("implementation_profile", sa.String(length=128), nullable=True),
        sa.Column("provider", sa.String(length=128), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("query", sa.Text(), nullable=True),
        sa.Column("conversation_context", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("source_snapshot_id", sa.String(length=128), nullable=True),
        sa.Column("config_hash", sa.String(length=128), nullable=True),
        sa.Column("tasks", sa.JSON(), nullable=False),
        sa.Column("task_results", sa.JSON(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("events", sa.JSON(), nullable=False),
        sa.Column("effective_config", sa.JSON(), nullable=False),
        sa.Column("scoring_versions", sa.JSON(), nullable=False),
        sa.Column(
            "planning_retrieval_scoring_version", sa.String(length=128), nullable=True
        ),
        sa.Column("retrieval_scoring_version", sa.String(length=128), nullable=True),
        sa.Column("domain_ranking_version", sa.String(length=128), nullable=True),
        sa.Column("retrieval", sa.JSON(), nullable=False),
        sa.Column("extra_data", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "conversation_id IS NULL OR owner_user_id IS NOT NULL",
            name="ck_runs_conversation_requires_owner",
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.user_id"],
            name="fk_runs_owner_user",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id", "owner_user_id"],
            ["conversations.conversation_id", "conversations.owner_user_id"],
            name="fk_runs_conversation_owner",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("run_id"),
        sa.UniqueConstraint(
            "conversation_id", "run_id", name="uq_runs_conversation_id"
        ),
    )
    op.create_index(
        "ix_runs_owner_created_at", "runs", ["owner_user_id", "created_at"]
    )

    op.create_table(
        "conversation_messages",
        sa.Column("message_id", sa.String(length=64), nullable=False),
        sa.Column("conversation_id", sa.String(length=64), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("run_id", sa.String(length=128), nullable=True),
        sa.CheckConstraint(
            "sequence_number >= 0", name="ck_conversation_messages_sequence"
        ),
        sa.CheckConstraint(
            "role IN ('USER', 'ASSISTANT')", name="ck_conversation_messages_role"
        ),
        sa.CheckConstraint(
            "length(btrim(content)) > 0", name="ck_conversation_messages_content"
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.conversation_id"],
            name="fk_conversation_messages_conversation",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id", "run_id"],
            ["runs.conversation_id", "runs.run_id"],
            name="fk_conversation_messages_run_same_conversation",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("message_id"),
        sa.UniqueConstraint(
            "conversation_id",
            "sequence_number",
            name="uq_conversation_messages_order",
        ),
    )


def downgrade() -> None:
    op.drop_table("conversation_messages")
    op.drop_index("ix_runs_owner_created_at", table_name="runs")
    op.drop_table("runs")
    op.drop_index("ix_conversations_owner_updated", table_name="conversations")
    op.drop_table("conversations")
