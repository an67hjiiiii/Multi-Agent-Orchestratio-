from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from dataclasses import replace

from app.core.types import SourceChunk


STOP = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "to",
    "of",
    "in",
    "on",
    "for",
    "with",
    "is",
    "are",
    "be",
    "this",
    "that",
    "và",
    "là",
    "của",
    "cho",
    "trong",
    "với",
    "một",
    "các",
    "những",
    "được",
    "hãy",
    "theo",
}

_TOKEN_RE = re.compile(r"[^\W_]+(?:[_'-][^\W_]+)*", re.UNICODE)


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


def estimate_tokens(text: str) -> int:
    """Tokenizer-independent conservative proxy used only for pre-call budgeting.

    Actual provider-reported token counts remain authoritative in run metrics.
    """
    clean = normalize_text(text)
    if not clean:
        return 0
    # Mixed Vietnamese/English text generally lands near 3-4 chars/token.
    return max(1, (len(clean) + 2) // 3)


def _stem_token(token: str) -> str:
    # Tiny deterministic English normalization; intentionally not a learned stemmer.
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    if token.endswith("es") and len(token) > 4:
        return token[:-2]
    if token.endswith("s") and len(token) > 3 and not token.endswith("ss"):
        return token[:-1]
    return token


def terms(text: str) -> set[str]:
    """Extract deterministic Unicode-aware lexical terms for local retrieval."""
    raw = _TOKEN_RE.findall(normalize_text(text).casefold())
    expanded = {
        piece
        for token in raw
        for piece in (token, *re.split(r"[_'-]", token))
        if len(piece) >= 2
    }
    normalized = {_stem_token(t) for t in expanded if t not in STOP}
    return normalized


def chunk_text(text: str, max_chars: int = 1200) -> list[str]:
    if isinstance(max_chars, bool) or not isinstance(max_chars, int) or max_chars < 1:
        raise ValueError("max_chars must be a positive integer")
    text = normalize_text(text)
    if not text:
        return []
    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    buf = ""
    for part in parts:
        if len(buf) + len(part) + 2 <= max_chars:
            buf = (buf + "\n\n" + part).strip()
        else:
            if buf:
                chunks.append(buf)
            if len(part) <= max_chars:
                buf = part
            else:
                for i in range(0, len(part), max_chars):
                    chunks.append(part[i:i+max_chars])
                buf = ""
    if buf:
        chunks.append(buf)
    return chunks


def make_chunks(source_name: str, text: str, max_chars: int = 1200) -> list[SourceChunk]:
    source_name = normalize_source_name(source_name)
    if not source_name:
        raise ValueError("source_name must not be empty")
    clean = normalize_text(text)
    source_id = "src_" + hashlib.sha256(
        (source_name + "\0" + clean).encode("utf-8")
    ).hexdigest()[:16]
    result: list[SourceChunk] = []
    for i, chunk in enumerate(chunk_text(clean, max_chars=max_chars)):
        result.append(SourceChunk(
            chunk_id=f"{source_id}_c{i:04d}",
            source_id=source_id,
            source_name=source_name,
            text=chunk,
            index=i,
        ))
    return result


def lexical_score(query: str, chunk: SourceChunk) -> float:
    q = terms(query)
    c = terms(chunk.text)
    if not q or not c:
        return 0.0
    overlap = len(q & c)
    coverage = overlap / max(1, len(q))
    density = overlap / max(1, len(c))
    return round(0.8 * coverage + 0.2 * density, 8)


def retrieve(
    query: str,
    chunks: list[SourceChunk],
    top_k: int = 6,
    min_score: float = 0.0,
) -> list[SourceChunk]:
    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1:
        raise ValueError("top_k must be a positive integer")
    if (
        not isinstance(min_score, (int, float))
        or isinstance(min_score, bool)
        or not math.isfinite(min_score)
        or min_score < 0
    ):
        raise ValueError("min_score must be a finite non-negative number")

    scored: list[SourceChunk] = []
    seen_ids: set[str] = set()
    for chunk in chunks:
        if not isinstance(chunk, SourceChunk):
            raise TypeError("chunks must contain SourceChunk values")
        if chunk.chunk_id in seen_ids:
            continue
        seen_ids.add(chunk.chunk_id)
        score = lexical_score(query, chunk)
        if score >= min_score and score > 0:
            scored.append(replace(chunk, score=score))
    scored.sort(key=lambda x: (-x.score, x.chunk_id, x.source_id, x.index))
    return scored[:top_k]


def apply_token_budget(
    chunks: list[SourceChunk], max_tokens: int
) -> tuple[list[SourceChunk], list[dict]]:
    if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or max_tokens < 1:
        raise ValueError("max_tokens must be a positive integer")

    selected: list[SourceChunk] = []
    dropped: list[dict] = []
    used = 0
    for chunk in chunks:
        if not isinstance(chunk, SourceChunk):
            raise TypeError("chunks must contain SourceChunk values")
        cost = estimate_tokens(chunk.text)
        if selected and used + cost > max_tokens:
            dropped.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "reason": "hard_context_token_cap",
                    "estimated_tokens": cost,
                }
            )
            continue
        if not selected and cost > max_tokens:
            # Preserve a bounded excerpt instead of silently exceeding the cap.
            char_cap = max(1, max_tokens * 3)
            excerpt = chunk.text[:char_cap]
            selected.append(replace(chunk, text=excerpt))
            used += estimate_tokens(excerpt)
            dropped.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "reason": "truncated_to_hard_context_token_cap",
                    "estimated_tokens": cost,
                }
            )
            continue
        selected.append(chunk)
        used += cost
    return selected, dropped
