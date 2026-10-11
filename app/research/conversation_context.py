from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


DEFAULT_MAX_MESSAGES = 6
DEFAULT_MAX_CHARS = 6_000


@dataclass(frozen=True)
class ConversationContext:
    """Bounded same-conversation history, never corpus evidence."""

    text: str = ""
    message_ids: tuple[str, ...] = ()
    truncated: bool = False

    def to_trace(self) -> dict[str, Any]:
        return {
            "message_ids": list(self.message_ids),
            "message_count": len(self.message_ids),
            "chars": len(self.text),
            "truncated": self.truncated,
            "source": "conversation_history",
            "is_rag_evidence": False,
        }


def build_conversation_context(
    conversation: Mapping[str, Any] | None,
    *,
    current_message_id: str | None = None,
    max_messages: int = DEFAULT_MAX_MESSAGES,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> ConversationContext:
    """Render only recent messages from one already-authorized conversation."""

    if not isinstance(conversation, Mapping):
        return ConversationContext()
    rows = conversation.get("messages")
    if not isinstance(rows, list):
        return ConversationContext()
    message_limit = max(0, int(max_messages))
    char_limit = max(0, int(max_chars))
    eligible = [
        item
        for item in rows
        if isinstance(item, Mapping)
        and str(item.get("message_id") or "") != str(current_message_id or "")
        and str(item.get("role") or "").upper() in {"USER", "ASSISTANT"}
        and isinstance(item.get("content"), str)
        and item.get("content", "").strip()
    ]
    selected = eligible[-message_limit:] if message_limit else []
    truncated = len(selected) < len(eligible)
    rendered_reversed: list[str] = []
    kept_ids_reversed: list[str] = []
    used = 0
    for item in reversed(selected):
        role = str(item.get("role") or "").upper()
        content = str(item.get("content") or "").strip()
        line = f"[{role}] {content}"
        remaining = char_limit - used
        if remaining <= 0:
            truncated = True
            break
        if len(line) > remaining:
            line = line[:remaining].rstrip()
            truncated = True
        if not line:
            truncated = True
            break
        rendered_reversed.append(line)
        kept_ids_reversed.append(str(item.get("message_id")))
        used += len(line)
        if used >= char_limit:
            if len(rendered_reversed) < len(selected):
                truncated = True
            break
    rendered = "\n".join(reversed(rendered_reversed))
    if len(rendered) > char_limit:
        rendered = rendered[:char_limit].rstrip()
        truncated = True
    return ConversationContext(
        text=rendered,
        message_ids=tuple(reversed(kept_ids_reversed)),
        truncated=truncated,
    )


__all__ = [
    "ConversationContext",
    "DEFAULT_MAX_CHARS",
    "DEFAULT_MAX_MESSAGES",
    "build_conversation_context",
]
