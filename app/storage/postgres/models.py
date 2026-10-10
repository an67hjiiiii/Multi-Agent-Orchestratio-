from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.storage.postgres.base import Base


class UserRecord(Base):
    """Persisted identity fields for the PostgreSQL foundation."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "email IS NOT NULL OR username IS NOT NULL",
            name="ck_users_login_identity",
        ),
        CheckConstraint("role IN ('USER', 'ADMIN')", name="ck_users_role"),
        UniqueConstraint("email", name="uq_users_email"),
        UniqueConstraint("username", name="uq_users_username"),
    )

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="USER")
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="ACTIVE", server_default="ACTIVE"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    knowledge_sources: Mapped[list[KnowledgeSourceRecord]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    conversations: Mapped[list[ConversationRecord]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    runs: Mapped[list[RunRecord]] = relationship(
        back_populates="owner",
        foreign_keys="RunRecord.owner_user_id",
    )
    sessions: Mapped[list[SessionRecord]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )


class SessionRecord(Base):
    """Hashed, expiring authentication sessions persisted by PostgreSQL."""

    __tablename__ = "sessions"
    __table_args__ = (
        Index("ix_sessions_user_expiry", "user_id", "expires_at"),
        UniqueConstraint("token_hash", name="uq_sessions_token_hash"),
    )

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[UserRecord] = relationship(back_populates="sessions")


class KnowledgeSourceRecord(Base):
    """Private source metadata; ownership is enforced by the user foreign key."""

    __tablename__ = "knowledge_sources"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PROCESSING', 'READY', 'FAILED')",
            name="ck_knowledge_sources_lifecycle",
        ),
        Index("ix_knowledge_sources_owner_status", "owner_user_id", "status"),
    )

    source_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_name: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="PROCESSING", server_default="PROCESSING"
    )
    file_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    owner: Mapped[UserRecord] = relationship(back_populates="knowledge_sources")
    chunks: Mapped[list[KnowledgeChunkRecord]] = relationship(
        back_populates="source",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="KnowledgeChunkRecord.chunk_index",
    )


class KnowledgeChunkRecord(Base):
    """Authoritative chunk text and provenance used to rebuild retrieval data."""

    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        CheckConstraint("chunk_index >= 0", name="ck_knowledge_chunks_index"),
        CheckConstraint(
            "content IS NOT NULL OR content_ref IS NOT NULL",
            name="ck_knowledge_chunks_content_reference",
        ),
        UniqueConstraint(
            "source_id", "chunk_index", name="uq_knowledge_chunks_source_index"
        ),
    )

    chunk_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    source_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("knowledge_sources.source_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    location: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_ref: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    provenance: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    indexing_version: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    source: Mapped[KnowledgeSourceRecord] = relationship(back_populates="chunks")


class ConversationRecord(Base):
    """Owner-scoped conversation header; messages remain ordered child rows."""

    __tablename__ = "conversations"
    __table_args__ = (
        CheckConstraint(
            "length(btrim(title)) > 0", name="ck_conversations_title_nonempty"
        ),
        UniqueConstraint(
            "conversation_id",
            "owner_user_id",
            name="uq_conversations_id_owner",
        ),
        ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.user_id"],
            name="fk_conversations_owner_user",
            ondelete="CASCADE",
        ),
        Index("ix_conversations_owner_updated", "owner_user_id", "updated_at"),
    )

    conversation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="conversation-v1",
        server_default="conversation-v1",
    )
    title: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        default="New conversation",
        server_default="New conversation",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    owner: Mapped[UserRecord] = relationship(back_populates="conversations")
    messages: Mapped[list[ConversationMessageRecord]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ConversationMessageRecord.sequence_number",
    )
    runs: Mapped[list[RunRecord]] = relationship(
        back_populates="conversation",
        foreign_keys="RunRecord.conversation_id",
    )


class RunRecord(Base):
    """Structured persistence shape for one processing/research run."""

    __tablename__ = "runs"
    __table_args__ = (
        CheckConstraint(
            "conversation_id IS NULL OR owner_user_id IS NOT NULL",
            name="ck_runs_conversation_requires_owner",
        ),
        UniqueConstraint(
            "conversation_id", "run_id", name="uq_runs_conversation_id"
        ),
        ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.user_id"],
            name="fk_runs_owner_user",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["conversation_id", "owner_user_id"],
            ["conversations.conversation_id", "conversations.owner_user_id"],
            name="fk_runs_conversation_owner",
            ondelete="RESTRICT",
        ),
        Index("ix_runs_owner_created_at", "owner_user_id", "created_at"),
    )

    run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    owner_user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    conversation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    condition: Mapped[str | None] = mapped_column(String(16), nullable=True)
    implementation_profile: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    provider: Mapped[str | None] = mapped_column(String(128), nullable=True)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    query: Mapped[str | None] = mapped_column(Text, nullable=True)
    conversation_context: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_snapshot_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    config_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tasks: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    task_results: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    metrics: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    events: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    effective_config: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    scoring_versions: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    planning_retrieval_scoring_version: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    retrieval_scoring_version: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    domain_ranking_version: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    retrieval: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    extra_data: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )

    owner: Mapped[UserRecord | None] = relationship(
        back_populates="runs", foreign_keys=[owner_user_id]
    )
    conversation: Mapped[ConversationRecord | None] = relationship(
        back_populates="runs", foreign_keys=[conversation_id]
    )


class ConversationMessageRecord(Base):
    """Ordered user/assistant turn with an optional same-thread run link."""

    __tablename__ = "conversation_messages"
    __table_args__ = (
        CheckConstraint(
            "sequence_number >= 0", name="ck_conversation_messages_sequence"
        ),
        CheckConstraint(
            "role IN ('USER', 'ASSISTANT')", name="ck_conversation_messages_role"
        ),
        CheckConstraint(
            "length(btrim(content)) > 0", name="ck_conversation_messages_content"
        ),
        UniqueConstraint(
            "conversation_id",
            "sequence_number",
            name="uq_conversation_messages_order",
        ),
        ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.conversation_id"],
            name="fk_conversation_messages_conversation",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["conversation_id", "run_id"],
            ["runs.conversation_id", "runs.run_id"],
            name="fk_conversation_messages_run_same_conversation",
            ondelete="RESTRICT",
        ),
    )

    message_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    run_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    conversation: Mapped[ConversationRecord] = relationship(back_populates="messages")
