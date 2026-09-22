"""Stable source-text preparation owned by document ingestion."""

from __future__ import annotations

import hashlib
import re
import unicodedata

from app.core.types import SourceChunk


def normalize_text(text: str) -> str:
    """Return one deterministic, UTF-8-safe representation of source text."""

    if not isinstance(text, str):
        raise TypeError("text must be a string")
    text = unicodedata.normalize("NFC", text)
    return (
        text.replace("\ufeff", "", 1)
        .replace("\x00", "")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .strip()
    )


def normalize_source_name(source_name: str) -> str:
    """Normalize the display name before it participates in source identity."""

    if not isinstance(source_name, str):
        raise TypeError("source_name must be a string")
    return (
        unicodedata.normalize("NFC", source_name)
        .replace("\ufeff", "", 1)
        .replace("\x00", "")
        .strip()
    )


def chunk_text(text: str, max_chars: int = 1200) -> list[str]:
    """Split normalized source text into stable ingestion chunks."""

    if isinstance(max_chars, bool) or not isinstance(max_chars, int) or max_chars < 1:
        raise ValueError("max_chars must be a positive integer")
    text = normalize_text(text)
    if not text:
        return []
    parts = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    chunks: list[str] = []
    buffer = ""
    for part in parts:
        if len(buffer) + len(part) + 2 <= max_chars:
            buffer = (buffer + "\n\n" + part).strip()
        else:
            if buffer:
                chunks.append(buffer)
            if len(part) <= max_chars:
                buffer = part
            else:
                for index in range(0, len(part), max_chars):
                    chunks.append(part[index:index + max_chars])
                buffer = ""
    if buffer:
        chunks.append(buffer)
    return chunks


def make_chunks(
    source_name: str,
    text: str,
    max_chars: int = 1200,
) -> list[SourceChunk]:
    """Create canonical chunk and source IDs for one persisted source."""

    source_name = normalize_source_name(source_name)
    if not source_name:
        raise ValueError("source_name must not be empty")
    clean = normalize_text(text)
    source_id = "src_" + hashlib.sha256(
        (source_name + "\0" + clean).encode("utf-8")
    ).hexdigest()[:16]
    return [
        SourceChunk(
            chunk_id=f"{source_id}_c{index:04d}",
            source_id=source_id,
            source_name=source_name,
            text=chunk,
            index=index,
        )
        for index, chunk in enumerate(chunk_text(clean, max_chars=max_chars))
    ]


__all__ = ["chunk_text", "make_chunks", "normalize_source_name", "normalize_text"]
