from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4


class ConversationStore:
    """Explicit file-backed conversation store for isolated dev/test use."""

    def __init__(self, root: str | Path = "data") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "conversations.json"
        self._lock = RLock()
        self._conversations: dict[str, dict[str, Any]] = {}
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self._conversations = {
                row["conversation_id"]: row
                for row in data.get("conversations", [])
                if isinstance(row, dict) and row.get("conversation_id")
            }

    def _save(self) -> None:
        payload = json.dumps(
            {"conversations": list(self._conversations.values())},
            ensure_ascii=False,
            indent=2,
        )
        temporary_path = None
        try:
            descriptor, temporary_path = tempfile.mkstemp(
                prefix=".conversations.", suffix=".tmp", dir=self.root, text=True
            )
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self.path)
            temporary_path = None
        finally:
            if temporary_path is not None:
                os.unlink(temporary_path)

    def create(self, title: str = "New conversation") -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        conversation = {
            "conversation_id": f"conv_{uuid4().hex[:16]}",
            "title": str(title or "New conversation").strip()[:120] or "New conversation",
            "created_at": now,
            "updated_at": now,
            "messages": [],
        }
        with self._lock:
            self._conversations[conversation["conversation_id"]] = conversation
            self._save()
        return dict(conversation)

    def add_message(
        self, conversation_id: str, role: str, content: str, run_id: str | None = None
    ) -> dict[str, Any]:
        role = str(role).upper()
        content = str(content or "").strip()
        if role not in {"USER", "ASSISTANT"} or not content:
            raise ValueError("message role or content is invalid")
        with self._lock:
            conversation = self._conversations.get(conversation_id)
            if conversation is None:
                raise LookupError("conversation not found")
            now = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
            message = {
                "message_id": f"msg_{uuid4().hex[:16]}",
                "conversation_id": conversation_id,
                "sequence_number": len(conversation["messages"]),
                "role": role,
                "content": content,
                "created_at": now,
                "run_id": run_id,
            }
            conversation["messages"].append(message)
            conversation["updated_at"] = now
            self._save()
            return dict(message)

    def get(self, conversation_id: str) -> dict[str, Any] | None:
        with self._lock:
            conversation = self._conversations.get(conversation_id)
            return None if conversation is None else json.loads(json.dumps(conversation))

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            rows = sorted(
                self._conversations.values(),
                key=lambda item: (item["updated_at"], item["conversation_id"]),
                reverse=True,
            )
            return [
                {key: row[key] for key in ("conversation_id", "title", "created_at", "updated_at")}
                for row in rows[: max(1, min(int(limit), 200))]
            ]
