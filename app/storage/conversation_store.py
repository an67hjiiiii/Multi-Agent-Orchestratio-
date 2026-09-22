from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any, Mapping

from app.conversation.contracts import Conversation, Message


CONVERSATION_SCHEMA_VERSION = "conversation-v1"
CONVERSATION_ROLES = frozenset({"USER", "ASSISTANT"})


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _clean_text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


class ConversationStore:
    """Small owner-scoped, file-backed conversation store.

    Conversations are deliberately separate from run persistence.  A run is
    still the immutable research record; this store only groups user/assistant
    turns and carries the owner boundary needed to reopen a thread safely.
    """

    def __init__(self, root: str | Path = "data/conversations") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

    @staticmethod
    def _path(root: Path, conversation_id: str) -> Path:
        return root / f"{conversation_id}.json"

    @staticmethod
    def _public(record: Mapping[str, Any]) -> dict[str, Any]:
        return Conversation.from_mapping(record).to_public_dict()

    def _read(self, conversation_id: str) -> dict[str, Any] | None:
        if not conversation_id or Path(conversation_id).name != conversation_id:
            return None
        path = self._path(self.root, conversation_id)
        if not path.is_file():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return None
        if not isinstance(raw, Mapping):
            return None
        messages = raw.get("messages", [])
        if not isinstance(messages, list):
            return None
        return dict(raw)

    def _write(self, record: Mapping[str, Any]) -> None:
        path = self._path(self.root, str(record["conversation_id"]))
        payload = json.dumps(record, ensure_ascii=False, indent=2)
        temporary_path: str | None = None
        try:
            fd, temporary_path = tempfile.mkstemp(
                prefix=f".{path.name}.", suffix=".tmp", dir=self.root, text=True
            )
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, path)
            temporary_path = None
        finally:
            if temporary_path is not None:
                try:
                    os.unlink(temporary_path)
                except FileNotFoundError:
                    pass

    def create(self, owner_user_id: str, title: str | None = None) -> dict[str, Any]:
        owner = _clean_text(owner_user_id)
        if not owner:
            raise ValueError("owner_user_id is required")
        now = _utc_now()
        record = {
            "schema_version": CONVERSATION_SCHEMA_VERSION,
            "conversation_id": f"conv_{uuid.uuid4().hex[:12]}",
            "owner_user_id": owner,
            "title": _clean_text(title)[:120] or "New conversation",
            "created_at": now,
            "updated_at": now,
            "messages": [],
        }
        with self._lock:
            self._write(record)
        return self._public(record)

    def get(self, conversation_id: str, owner_user_id: str) -> dict[str, Any] | None:
        with self._lock:
            record = self._read(conversation_id)
        if record is None or str(record.get("owner_user_id") or "") != str(owner_user_id):
            return None
        return self._public(record)

    def list(self, owner_user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        owner = str(owner_user_id)
        bounded_limit = max(1, min(int(limit), 200))
        rows: list[dict[str, Any]] = []
        with self._lock:
            for path in self.root.glob("conv_*.json"):
                record = self._read(path.stem)
                if record is not None and str(record.get("owner_user_id") or "") == owner:
                    rows.append(self._public(record))
        rows.sort(key=lambda item: (str(item.get("updated_at") or ""), str(item.get("conversation_id") or "")), reverse=True)
        return rows[:bounded_limit]

    def append_message(
        self,
        conversation_id: str,
        owner_user_id: str,
        *,
        role: str,
        content: str,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        normalized_role = _clean_text(role).upper()
        normalized_content = _clean_text(content)
        if normalized_role not in CONVERSATION_ROLES:
            raise ValueError("role must be USER or ASSISTANT")
        if not normalized_content:
            raise ValueError("content is required")
        with self._lock:
            record = self._read(conversation_id)
            if record is None or str(record.get("owner_user_id") or "") != str(owner_user_id):
                raise KeyError(conversation_id)
            messages = record.setdefault("messages", [])
            if not isinstance(messages, list):
                messages = []
                record["messages"] = messages
            message = Message(
                message_id=f"msg_{uuid.uuid4().hex[:12]}",
                conversation_id=conversation_id,
                role=normalized_role,
                content=normalized_content,
                created_at=_utc_now(),
                run_id=run_id,
            ).to_dict()
            messages.append(message)
            if normalized_role == "USER" and str(record.get("title") or "New conversation") == "New conversation":
                record["title"] = normalized_content[:120]
            record["updated_at"] = _utc_now()
            self._write(record)
            return dict(message)

    def link_message_run(
        self,
        conversation_id: str,
        owner_user_id: str,
        message_id: str,
        run_id: str,
    ) -> dict[str, Any] | None:
        """Attach the immutable run identity to an already persisted turn."""

        with self._lock:
            record = self._read(conversation_id)
            if record is None or str(record.get("owner_user_id") or "") != str(owner_user_id):
                return None
            for message in record.get("messages", []):
                if isinstance(message, dict) and message.get("message_id") == message_id:
                    message["run_id"] = run_id
                    record["updated_at"] = _utc_now()
                    self._write(record)
                    return dict(message)
        return None
