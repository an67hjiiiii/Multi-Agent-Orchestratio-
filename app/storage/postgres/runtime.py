from __future__ import annotations

import hashlib
import re
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.auth.store import (
    AUTH_SCHEMA_VERSION,
    DEFAULT_SESSION_TTL_SECONDS,
    PASSWORD_MIN_LENGTH,
    USER_ROLES,
    DuplicateUserError,
    InvalidCredentialsError,
    InvalidSessionError,
    _iso,
    _normalized_email,
    _normalized_username,
    _password_hash,
    _password_matches,
    _parse_iso,
    _token_hash,
)
from app.core.types import SourceChunk
from app.retrieval.text import make_chunks, normalize_text
from app.storage.postgres.models import (
    ConversationMessageRecord,
    ConversationRecord,
    KnowledgeChunkRecord,
    KnowledgeSourceRecord,
    RunRecord,
    SessionRecord,
    UserRecord,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _public_user(user: UserRecord) -> dict[str, Any]:
    return {
        "id": user.user_id,
        "user_id": user.user_id,
        "email": user.email,
        "username": user.username,
        "name": user.display_name,
        "display_name": user.display_name,
        "role": user.role.upper(),
        "created_at": _iso(user.created_at),
        "updated_at": _iso(user.updated_at),
        "last_login_at": None if user.last_login_at is None else _iso(user.last_login_at),
        "status": user.status.upper(),
    }


def _public_session(session: SessionRecord) -> dict[str, Any]:
    return {
        "session_id": session.session_id,
        "user_id": session.user_id,
        "created_at": _iso(session.created_at),
        "expires_at": _iso(session.expires_at),
    }


class PostgresAuthStore:
    """PostgreSQL implementation of the existing user/session contract."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        session_ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS,
    ) -> None:
        self.session_factory = session_factory
        self.session_ttl_seconds = max(60, int(session_ttl_seconds))
        self._bootstrap_admin_from_environment()

    def _bootstrap_admin_from_environment(self) -> None:
        email = _normalized_email(os.getenv("LOCAL_AUTH_ADMIN_EMAIL"))
        password = os.getenv("LOCAL_AUTH_ADMIN_PASSWORD", "")
        if not email or len(password) < PASSWORD_MIN_LENGTH:
            return
        with self.session_factory.begin() as db:
            if db.scalar(select(func.count()).select_from(UserRecord)):
                return
            now = _now()
            db.add(UserRecord(
                user_id=f"usr_{secrets.token_urlsafe(12)}",
                email=email,
                display_name=email.split("@", 1)[0],
                password_hash=_password_hash(password),
                role="ADMIN",
                status="ACTIVE",
                created_at=now,
                updated_at=now,
            ))

    def register(
        self,
        *,
        password: str,
        email: str | None = None,
        username: str | None = None,
        display_name: str | None = None,
        role: str | None = None,
    ) -> dict[str, Any]:
        email_value = _normalized_email(email)
        username_value = _normalized_username(username)
        if not email_value and not username_value:
            raise ValueError("email or username is required")
        if email_value and ("@" not in email_value or len(email_value) > 254):
            raise ValueError("email is invalid")
        if username_value and not re.fullmatch(
            r"^[A-Za-z0-9][A-Za-z0-9_.-]{1,63}$", username_value
        ):
            raise ValueError("username is invalid")
        if not isinstance(password, str) or len(password) < PASSWORD_MIN_LENGTH:
            raise ValueError(f"password must be at least {PASSWORD_MIN_LENGTH} characters")
        requested_role = str(role or "USER").strip().upper()
        if requested_role not in USER_ROLES:
            raise ValueError("role must be USER or ADMIN")

        now = _now()
        try:
            with self.session_factory.begin() as db:
                existing = db.scalar(select(UserRecord.user_id).where(or_(
                    UserRecord.email == email_value if email_value else False,
                    UserRecord.username == username_value if username_value else False,
                )))
                if existing:
                    raise DuplicateUserError("email or username is already registered")
                assigned_role = requested_role if not db.scalar(
                    select(func.count()).select_from(UserRecord)
                ) else "USER"
                name = (display_name or username_value or email_value.split("@", 1)[0]).strip()
                record = UserRecord(
                    user_id=f"usr_{secrets.token_urlsafe(12)}",
                    email=email_value or None,
                    username=username_value or None,
                    display_name=name,
                    role=assigned_role,
                    status="ACTIVE",
                    password_hash=_password_hash(password),
                    created_at=now,
                    updated_at=now,
                )
                db.add(record)
                db.flush()
                result = _public_user(record)
        except IntegrityError as exc:
            raise DuplicateUserError("email or username is already registered") from exc
        return result

    def authenticate(self, *, identifier: str, password: str) -> tuple[dict[str, Any], str, dict[str, Any]]:
        normalized = str(identifier or "").strip().lower()
        if not normalized or not isinstance(password, str):
            raise InvalidCredentialsError("invalid credentials")
        now = _now()
        with self.session_factory.begin() as db:
            user = db.scalar(select(UserRecord).where(or_(
                UserRecord.email == normalized, UserRecord.username == normalized
            )))
            if (
                user is None
                or user.status.upper() != "ACTIVE"
                or not _password_matches(password, user.password_hash)
            ):
                raise InvalidCredentialsError("invalid credentials")
            user.last_login_at = now
            user.updated_at = now
            token = secrets.token_urlsafe(32)
            record = SessionRecord(
                session_id=f"ses_{secrets.token_urlsafe(12)}",
                user_id=user.user_id,
                token_hash=_token_hash(token),
                created_at=now,
                expires_at=now + timedelta(seconds=self.session_ttl_seconds),
            )
            db.add(record)
            db.flush()
            return _public_user(user), token, _public_session(record)

    def create_session(self, user_id: str) -> tuple[str, dict[str, Any]]:
        now = _now()
        token = secrets.token_urlsafe(32)
        with self.session_factory.begin() as db:
            user = db.get(UserRecord, user_id)
            if user is None or user.status.upper() != "ACTIVE":
                raise InvalidCredentialsError("user not found")
            record = SessionRecord(
                session_id=f"ses_{secrets.token_urlsafe(12)}",
                user_id=user_id,
                token_hash=_token_hash(token),
                created_at=now,
                expires_at=now + timedelta(seconds=self.session_ttl_seconds),
            )
            db.add(record)
            db.flush()
            return token, _public_session(record)

    def resolve(self, token: str | None) -> dict[str, Any]:
        if not isinstance(token, str) or not token.strip():
            raise InvalidSessionError("authentication is required")
        digest = _token_hash(token.strip())
        now = _now()
        with self.session_factory() as db:
            row = db.execute(
                select(SessionRecord, UserRecord)
                .join(UserRecord, UserRecord.user_id == SessionRecord.user_id)
                .where(
                    SessionRecord.token_hash == digest,
                    SessionRecord.revoked_at.is_(None),
                    SessionRecord.expires_at > now,
                    UserRecord.status == "ACTIVE",
                )
            ).first()
            if row is None:
                raise InvalidSessionError("session is invalid or expired")
            return _public_user(row[1])

    def revoke(self, token: str | None) -> bool:
        if not isinstance(token, str) or not token.strip():
            return False
        with self.session_factory.begin() as db:
            record = db.scalar(select(SessionRecord).where(
                SessionRecord.token_hash == _token_hash(token.strip()),
                SessionRecord.revoked_at.is_(None),
            ))
            if record is None:
                return False
            record.revoked_at = _now()
            return True

    def session_for_token(self, token: str | None) -> dict[str, Any] | None:
        if not isinstance(token, str) or not token.strip():
            return None
        now = _now()
        with self.session_factory() as db:
            record = db.scalar(select(SessionRecord).where(
                SessionRecord.token_hash == _token_hash(token.strip()),
                SessionRecord.revoked_at.is_(None),
                SessionRecord.expires_at > now,
            ))
            return None if record is None else _public_session(record)

    def list_users(self, *, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 500))
        offset = max(0, int(offset))
        with self.session_factory() as db:
            rows = db.scalars(select(UserRecord).order_by(
                UserRecord.created_at.desc(), UserRecord.user_id.desc()
            ).offset(offset).limit(limit)).all()
            return [_public_user(row) for row in rows]

    def user_count(self) -> int:
        with self.session_factory() as db:
            return int(db.scalar(select(func.count()).select_from(UserRecord)) or 0)

    def status(self) -> dict[str, Any]:
        now = _now()
        with self.session_factory() as db:
            return {
                "schema_version": AUTH_SCHEMA_VERSION,
                "local_only": True,
                "user_count": int(db.scalar(select(func.count()).select_from(UserRecord)) or 0),
                "admin_count": int(db.scalar(select(func.count()).select_from(UserRecord).where(UserRecord.role == "ADMIN")) or 0),
                "active_session_count": int(db.scalar(select(func.count()).select_from(SessionRecord).where(
                    SessionRecord.revoked_at.is_(None), SessionRecord.expires_at > now
                )) or 0),
                "session_ttl_seconds": self.session_ttl_seconds,
            }


class PostgresSourceStore:
    """A source/chunk store bound to one authenticated owner."""

    def __init__(self, session_factory: sessionmaker[Session], owner_user_id: str) -> None:
        self.session_factory = session_factory
        self.owner_user_id = owner_user_id

    def import_text(
        self,
        source_name: str,
        text: str,
        *,
        provenance: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        clean_text = normalize_text(text)
        if not str(source_name or "").strip():
            raise ValueError("source_name must not be empty")
        if not clean_text:
            raise ValueError("text must not be empty")
        original_source_id = "src_" + hashlib.sha256(
            (str(source_name).strip() + "\0" + clean_text).encode("utf-8")
        ).hexdigest()[:16]
        source_id = "src_" + hashlib.sha256(
            f"{self.owner_user_id}\0{original_source_id}".encode("utf-8")
        ).hexdigest()[:16]
        metadata = {
            "storage": "postgresql",
            "indexing_version": "s2-lifecycle-v1",
            **(dict(provenance) if isinstance(provenance, dict) else {}),
        }
        source_provenance = {
            **metadata,
            "source_id": source_id,
            "source_name": str(source_name).strip(),
            "source_hash": hashlib.sha256(clean_text.encode("utf-8")).hexdigest(),
            "source_version": source_id,
        }
        metadata = source_provenance
        now = _now()
        with self.session_factory.begin() as db:
            source = db.get(KnowledgeSourceRecord, source_id)
            if source is None:
                db.add(
                    KnowledgeSourceRecord(
                        source_id=source_id,
                        owner_user_id=self.owner_user_id,
                        source_name=str(source_name).strip(),
                        status="PROCESSING",
                        display_metadata=metadata,
                        created_at=now,
                        updated_at=now,
                    )
                )
            elif source.owner_user_id != self.owner_user_id:
                raise PermissionError("source belongs to another owner")
            else:
                source.status = "PROCESSING"
                source.display_metadata = metadata
                source.updated_at = now

        try:
            chunks = make_chunks(
                str(source_name).strip(), clean_text, provenance=source_provenance
            )
            if not chunks:
                raise ValueError("text must not be empty")
            owned_chunks = [
                SourceChunk(
                    chunk_id=f"{source_id}_c{chunk.index:04d}",
                    source_id=source_id,
                    source_name=chunk.source_name,
                    text=chunk.text,
                    index=chunk.index,
                    provenance={
                        **chunk.provenance,
                        "chunk_id": f"{source_id}_c{chunk.index:04d}",
                    },
                )
                for chunk in chunks
            ]
        except Exception as exc:
            self.mark_failed(source_id, exc)
            raise

        try:
            with self.session_factory.begin() as db:
                source = db.get(KnowledgeSourceRecord, source_id)
                if source is None or source.owner_user_id != self.owner_user_id:
                    raise PermissionError("source belongs to another owner")
                existing = set(db.scalars(select(KnowledgeChunkRecord.chunk_id).where(
                    KnowledgeChunkRecord.source_id == source_id
                )).all())
                added = [chunk for chunk in owned_chunks if chunk.chunk_id not in existing]
                db.add_all([
                    KnowledgeChunkRecord(
                        chunk_id=chunk.chunk_id,
                        source_id=source_id,
                        chunk_index=chunk.index,
                        content=chunk.text,
                        provenance=dict(chunk.provenance),
                        indexing_version="s2-lifecycle-v1",
                    )
                    for chunk in added
                ])
                source.status = "READY"
                source.display_metadata = {**metadata, "status": "READY"}
                source.updated_at = _now()
        except Exception as exc:
            self.mark_failed(source_id, exc)
            raise
        return {
            "source_id": source_id,
            "source_name": source_name,
            "chunks_added": len(added),
            "total_chunks_for_source": len(owned_chunks),
            "source_hash": source_provenance["source_hash"],
            "source_version": source_id,
            "provenance": dict(source_provenance),
            "snapshot_id": self.snapshot_id(),
        }

    def mark_failed(self, source_id: str, error: Exception | str) -> None:
        """Persist a terminal FAILED state without exposing source contents."""

        with self.session_factory.begin() as db:
            source = db.scalar(
                select(KnowledgeSourceRecord).where(
                    KnowledgeSourceRecord.source_id == source_id,
                    KnowledgeSourceRecord.owner_user_id == self.owner_user_id,
                )
            )
            if source is None:
                return
            source.status = "FAILED"
            source.display_metadata = {
                **(source.display_metadata or {}),
                "status": "FAILED",
                "error_type": type(error).__name__ if isinstance(error, Exception) else "IngestionError",
                "error": str(error),
            }
            source.updated_at = _now()

    def source_status(self, source_id: str) -> dict[str, Any] | None:
        with self.session_factory() as db:
            source = db.scalar(
                select(KnowledgeSourceRecord).where(
                    KnowledgeSourceRecord.source_id == source_id,
                    KnowledgeSourceRecord.owner_user_id == self.owner_user_id,
                )
            )
            if source is None:
                return None
            return {
                "source_id": source.source_id,
                "source_name": source.source_name,
                "status": source.status,
                "metadata": dict(source.display_metadata or {}),
            }

    def chunks(self, source_ids: list[str] | None = None) -> list[SourceChunk]:
        with self.session_factory() as db:
            filters = [
                KnowledgeSourceRecord.owner_user_id == self.owner_user_id,
                KnowledgeSourceRecord.status == "READY",
            ]
            if source_ids is not None:
                filters.append(KnowledgeChunkRecord.source_id.in_(source_ids))
            rows = db.scalars(
                select(KnowledgeChunkRecord)
                .join(KnowledgeSourceRecord)
                .where(*filters)
                .order_by(KnowledgeChunkRecord.source_id, KnowledgeChunkRecord.chunk_index)
            ).all()
            return [self._chunk(row) for row in rows]

    def validate_source_selection(self, source_ids: list[str]) -> None:
        """Reject missing, non-ready, or foreign source IDs before retrieval."""

        requested = {str(source_id) for source_id in source_ids if str(source_id)}
        if not requested:
            return
        with self.session_factory() as db:
            available = set(
                db.scalars(
                    select(KnowledgeSourceRecord.source_id).where(
                        KnowledgeSourceRecord.owner_user_id == self.owner_user_id,
                        KnowledgeSourceRecord.status == "READY",
                        KnowledgeSourceRecord.source_id.in_(requested),
                    )
                ).all()
            )
        if available != requested:
            raise LookupError("source not found")

    def list_sources(self) -> list[dict[str, Any]]:
        with self.session_factory() as db:
            rows = db.execute(
                select(KnowledgeSourceRecord, func.count(KnowledgeChunkRecord.chunk_id))
                .outerjoin(KnowledgeChunkRecord)
                .where(KnowledgeSourceRecord.owner_user_id == self.owner_user_id)
                .group_by(KnowledgeSourceRecord.source_id)
                .order_by(KnowledgeSourceRecord.source_name, KnowledgeSourceRecord.source_id)
            ).all()
            return [{"source_id": source.source_id, "source_name": source.source_name,
                     "chunk_count": int(count)} for source, count in rows]

    def source(self, source_id: str) -> dict[str, Any] | None:
        with self.session_factory() as db:
            source = db.scalar(select(KnowledgeSourceRecord).where(
                KnowledgeSourceRecord.source_id == source_id,
                KnowledgeSourceRecord.owner_user_id == self.owner_user_id,
            ))
            if source is None:
                return None
            chunks = db.scalars(select(KnowledgeChunkRecord).where(
                KnowledgeChunkRecord.source_id == source_id
            ).order_by(KnowledgeChunkRecord.chunk_index)).all()
            return {"source_id": source_id, "source_name": source.source_name,
                    "status": source.status,
                    "provenance": dict(source.display_metadata or {}),
                    "metadata": dict(source.display_metadata or {}),
                    "chunks": [self._chunk(row).__dict__ for row in chunks]}

    def chunk(self, chunk_id: str) -> dict[str, Any] | None:
        with self.session_factory() as db:
            row = db.scalar(
                select(KnowledgeChunkRecord)
                .join(KnowledgeSourceRecord)
                .where(
                    KnowledgeChunkRecord.chunk_id == chunk_id,
                    KnowledgeSourceRecord.owner_user_id == self.owner_user_id,
                )
            )
            return None if row is None else self._chunk(row).__dict__.copy()

    def snapshot_id(self) -> str:
        chunks = self.chunks()
        payload = "\n".join(
            f"{c.chunk_id}\0{c.source_id}\0{c.source_name}\0{c.index}\0{c.text}"
            for c in sorted(chunks, key=lambda item: item.chunk_id)
        )
        return "corpus_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def clear(self) -> None:
        with self.session_factory.begin() as db:
            source_ids = select(KnowledgeSourceRecord.source_id).where(
                KnowledgeSourceRecord.owner_user_id == self.owner_user_id
            )
            db.execute(delete(KnowledgeSourceRecord).where(KnowledgeSourceRecord.source_id.in_(source_ids)))

    @staticmethod
    def _chunk(row: KnowledgeChunkRecord) -> SourceChunk:
        return SourceChunk(
            chunk_id=row.chunk_id,
            source_id=row.source_id,
            source_name=row.source.source_name,
            text=row.content or "",
            index=row.chunk_index,
            provenance=dict(row.provenance or {}),
        )


class PostgresRunStore:
    """Run persistence that cannot read or overwrite another owner's runs."""

    _FIELDS = (
        "run_id", "created_at", "condition", "implementation_profile", "provider", "model",
        "query", "conversation_context", "status", "answer", "source_snapshot_id", "config_hash",
        "tasks", "task_results", "metrics", "events", "effective_config", "scoring_versions",
        "planning_retrieval_scoring_version", "retrieval_scoring_version", "domain_ranking_version", "retrieval",
    )

    def __init__(self, session_factory: sessionmaker[Session], owner_user_id: str,
                 conversation_id: str | None = None) -> None:
        self.session_factory = session_factory
        self.owner_user_id = owner_user_id
        self.conversation_id = conversation_id

    def save(self, run: dict[str, Any]) -> None:
        created_at = _parse_iso(run.get("created_at"))
        with self.session_factory.begin() as db:
            record = db.get(RunRecord, run["run_id"])
            if record is not None and record.owner_user_id != self.owner_user_id:
                raise PermissionError("run belongs to another owner")
            values: dict[str, Any] = {
                field: run[field] for field in self._FIELDS if field in run
            }
            values.update(
                owner_user_id=self.owner_user_id,
                conversation_id=self.conversation_id,
                created_at=created_at,
                extra_data={
                    **run,
                    **({"conversation_id": self.conversation_id} if self.conversation_id else {}),
                },
            )
            if record is None:
                for field, default in {
                    "tasks": [], "task_results": [], "metrics": {}, "events": [],
                    "effective_config": {}, "scoring_versions": {}, "retrieval": {},
                }.items():
                    values.setdefault(field, default)
                record = RunRecord(**values)
                db.add(record)
            else:
                for field, value in values.items():
                    setattr(record, field, value)

    def get(self, run_id: str) -> dict[str, Any] | None:
        with self.session_factory() as db:
            row = db.scalar(select(RunRecord).where(
                RunRecord.run_id == run_id, RunRecord.owner_user_id == self.owner_user_id
            ))
            return None if row is None else dict(row.extra_data)

    def list(self, limit: int = 30) -> list[dict[str, Any]]:
        with self.session_factory() as db:
            rows = db.scalars(select(RunRecord).where(
                RunRecord.owner_user_id == self.owner_user_id
            ).order_by(RunRecord.created_at.desc(), RunRecord.run_id.desc()).limit(limit)).all()
            return [{key: row.extra_data.get(key) for key in
                     ("run_id", "created_at", "condition", "query", "status")} for row in rows]


class PostgresConversationStore:
    """Owner-scoped conversation and ordered message persistence."""

    def __init__(self, session_factory: sessionmaker[Session], owner_user_id: str) -> None:
        self.session_factory = session_factory
        self.owner_user_id = owner_user_id

    def create(self, title: str = "New conversation") -> dict[str, Any]:
        title = str(title or "New conversation").strip()[:120] or "New conversation"
        now = _now()
        record = ConversationRecord(
            conversation_id=f"conv_{uuid4().hex[:16]}", owner_user_id=self.owner_user_id,
            title=title, created_at=now, updated_at=now,
        )
        with self.session_factory.begin() as db:
            db.add(record)
            db.flush()
        return self.get(record.conversation_id) or {}

    def add_message(self, conversation_id: str, role: str, content: str,
                    run_id: str | None = None) -> dict[str, Any]:
        role = str(role).upper()
        content = str(content or "").strip()
        if role not in {"USER", "ASSISTANT"} or not content:
            raise ValueError("message role or content is invalid")
        now = _now()
        with self.session_factory.begin() as db:
            conversation = db.scalar(select(ConversationRecord).where(
                ConversationRecord.conversation_id == conversation_id,
                ConversationRecord.owner_user_id == self.owner_user_id,
            ).with_for_update())
            if conversation is None:
                raise LookupError("conversation not found")
            current_sequence = db.scalar(select(func.max(
                ConversationMessageRecord.sequence_number
            )).where(ConversationMessageRecord.conversation_id == conversation_id))
            next_sequence = int(current_sequence if current_sequence is not None else -1) + 1
            message = ConversationMessageRecord(
                message_id=f"msg_{uuid4().hex[:16]}", conversation_id=conversation_id,
                sequence_number=next_sequence, role=role, content=content, run_id=run_id,
                created_at=now,
            )
            conversation.updated_at = now
            db.add(message)
            db.flush()
            message_id = message.message_id
        return {"message_id": message_id, "conversation_id": conversation_id,
                "sequence_number": next_sequence, "role": role, "content": content,
                "created_at": _iso(now), "run_id": run_id}

    def get(self, conversation_id: str) -> dict[str, Any] | None:
        with self.session_factory() as db:
            conversation = db.scalar(select(ConversationRecord).where(
                ConversationRecord.conversation_id == conversation_id,
                ConversationRecord.owner_user_id == self.owner_user_id,
            ))
            if conversation is None:
                return None
            messages = db.scalars(select(ConversationMessageRecord).where(
                ConversationMessageRecord.conversation_id == conversation_id
            ).order_by(ConversationMessageRecord.sequence_number)).all()
            return {
                "conversation_id": conversation.conversation_id,
                "title": conversation.title,
                "created_at": _iso(conversation.created_at),
                "updated_at": _iso(conversation.updated_at),
                "messages": [{
                    "message_id": row.message_id,
                    "conversation_id": row.conversation_id,
                    "sequence_number": row.sequence_number,
                    "role": row.role,
                    "content": row.content,
                    "created_at": _iso(row.created_at),
                    "run_id": row.run_id,
                } for row in messages],
            }

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        with self.session_factory() as db:
            rows = db.scalars(select(ConversationRecord).where(
                ConversationRecord.owner_user_id == self.owner_user_id
            ).order_by(ConversationRecord.updated_at.desc()).limit(max(1, min(limit, 200)))).all()
            return [{"conversation_id": row.conversation_id, "title": row.title,
                     "created_at": _iso(row.created_at), "updated_at": _iso(row.updated_at)} for row in rows]
