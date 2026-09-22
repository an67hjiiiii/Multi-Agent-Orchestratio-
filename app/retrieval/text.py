from __future__ import annotations

import math
import re
from collections.abc import Iterable
from dataclasses import replace

from app.core.types import SourceChunk
from app.ingestion.text import (
    chunk_text,
    make_chunks,
    normalize_source_name,
    normalize_text,
)
from app.research.registry import REGISTRY

# These source-lifecycle helpers remain available from this historical module
# for compatibility; their implementation is owned by app.ingestion.text.


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

# These identities describe the deterministic ranking layers.  Domain-aware
# ordering is kept separate from the lexical score so existing score consumers
# retain the original semantics.
RETRIEVAL_SCORING_VERSION = "lexical-overlap-v1"
DOMAIN_RANKING_VERSION = "canonical-registry-domain-v1"


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


def _canonical_domain_terms() -> dict[str, frozenset[str]]:
    """Build searchable terms from the canonical domain registry metadata."""

    result: dict[str, frozenset[str]] = {}
    for domain, metadata in REGISTRY.items():
        values: list[str] = [domain]
        for field_name in ("name", "scope"):
            value = metadata.get(field_name)
            if isinstance(value, str):
                values.append(value)
        capabilities = metadata.get("capabilities", [])
        if isinstance(capabilities, (list, tuple, set, frozenset)):
            values.extend(value for value in capabilities if isinstance(value, str))
        result[domain] = frozenset(
            token for value in values for token in terms(value)
        )
    return result


_CANONICAL_DOMAIN_TERMS = _canonical_domain_terms()


def domain_compatibility(chunk: SourceChunk, task_domain: str | None) -> int:
    """Return a conservative compatibility rank for one task domain.

    A source-name match is the strongest available local metadata signal. A
    content match is weaker because content can legitimately serve multiple
    domains. A zero result means no canonical metadata signal was found; it
    never means that the candidate is unsafe to discard.
    """

    if not isinstance(task_domain, str) or not task_domain.strip():
        return 0
    canonical_terms = _CANONICAL_DOMAIN_TERMS.get(task_domain.strip())
    if not canonical_terms:
        return 0
    source_name_terms = terms(chunk.source_name)
    if source_name_terms.intersection(canonical_terms):
        return 2
    if terms(chunk.text).intersection(canonical_terms):
        return 1
    return 0


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
    *,
    domain: str | None = None,
    task_domain: str | None = None,
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
    if domain is not None and task_domain is not None and domain != task_domain:
        raise ValueError("domain and task_domain must identify the same domain")
    requested_domain = task_domain if task_domain is not None else domain

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
    scored.sort(
        key=lambda x: (
            -domain_compatibility(x, requested_domain),
            -x.score,
            x.chunk_id,
            x.source_id,
            x.index,
        )
    )
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
            excerpt = truncate_to_token_budget(chunk.text, max_tokens)
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


def estimate_context_tokens(chunks: Iterable[SourceChunk]) -> int:
    """Return the shared pre-call token estimate for selected context."""

    total = 0
    for chunk in chunks:
        if not isinstance(chunk, SourceChunk):
            raise TypeError("chunks must contain SourceChunk values")
        total += estimate_tokens(chunk.text)
    return total


def truncate_to_token_budget(text: str, max_tokens: int) -> str:
    """Return normalized text whose shared estimate fits the requested cap."""

    if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or max_tokens < 0:
        raise ValueError("max_tokens must be a non-negative integer")
    clean = normalize_text(text)
    if max_tokens == 0 or not clean:
        return ""

    excerpt = clean[: max_tokens * 3]
    while excerpt and estimate_tokens(excerpt) > max_tokens:
        excerpt = excerpt[:-1]
    return excerpt
