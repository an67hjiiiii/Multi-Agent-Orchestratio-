from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
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
