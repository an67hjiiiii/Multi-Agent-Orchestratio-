"""Typed, lossless adapters for the P0 conversation persistence shape."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping


def _extra(value: Mapping[str, Any], known: set[str]) -> dict[str, Any]:
    return {key: deepcopy(item) for key, item in value.items() if key not in known}


@dataclass(frozen=True)
class Message:
    message_id: str
    conversation_id: str
    role: str
    content: str
    created_at: str | None = None
    run_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "Message":
        if not isinstance(value, Mapping):
            raise TypeError("message must be a mapping")
        message_id = value.get("message_id")
        conversation_id = value.get("conversation_id")
        if not isinstance(message_id, str) or not message_id:
            raise ValueError("message_id is required")
        if not isinstance(conversation_id, str) or not conversation_id:
            raise ValueError("conversation_id is required")
        known = {"message_id", "conversation_id", "role", "content", "created_at", "run_id"}
        return cls(
            message_id=message_id,
            conversation_id=conversation_id,
            role=str(value.get("role") or ""),
            content=str(value.get("content") or ""),
            created_at=value.get("created_at"),
            run_id=value.get("run_id"),
            extra=_extra(value, known),
        )

    def to_dict(self) -> dict[str, Any]:
        result = deepcopy(self.extra)
        result.update({
            "message_id": self.message_id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at,
            "run_id": self.run_id,
        })
        return result


@dataclass(frozen=True)
class Conversation:
    conversation_id: str
    owner_user_id: str
    schema_version: str = "conversation-v1"
    title: str = "New conversation"
    created_at: str | None = None
    updated_at: str | None = None
    messages: list[Message] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "Conversation":
        if not isinstance(value, Mapping):
            raise TypeError("conversation must be a mapping")
        conversation_id = value.get("conversation_id")
        owner_user_id = value.get("owner_user_id")
        if not isinstance(conversation_id, str) or not conversation_id:
            raise ValueError("conversation_id is required")
        if not isinstance(owner_user_id, str) or not owner_user_id:
            raise ValueError("owner_user_id is required")
        raw_messages = value.get("messages") or []
        if not isinstance(raw_messages, list):
            raise TypeError("conversation messages must be a list")
        known = {"schema_version", "conversation_id", "owner_user_id", "title", "created_at", "updated_at", "messages"}
        return cls(
            conversation_id=conversation_id,
            owner_user_id=owner_user_id,
            schema_version=str(value.get("schema_version") or "conversation-v1"),
            title=str(value.get("title") or "New conversation"),
            created_at=value.get("created_at"),
            updated_at=value.get("updated_at"),
            messages=[Message.from_mapping(item) for item in raw_messages if isinstance(item, Mapping)],
            extra=_extra(value, known),
        )

    def to_dict(self) -> dict[str, Any]:
        result = deepcopy(self.extra)
        result["schema_version"] = self.schema_version
        result.update({
            "conversation_id": self.conversation_id,
            "owner_user_id": self.owner_user_id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "messages": [message.to_dict() for message in self.messages],
        })
        return result

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "owner_user_id": self.owner_user_id,
            "title": self.title or "New conversation",
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "messages": [message.to_dict() for message in self.messages],
        }


__all__ = ["Conversation", "Message"]
