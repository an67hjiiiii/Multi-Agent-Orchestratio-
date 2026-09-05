from __future__ import annotations

import pytest

from app.core.citations import validate_citations
from app.core.types import SourceChunk
from app.retrieval.text import (
    apply_token_budget,
    estimate_tokens,
    make_chunks,
    retrieve,
    terms,
)


def _chunk(chunk_id: str, text: str, index: int = 0) -> SourceChunk:
    return SourceChunk(
        chunk_id=chunk_id,
        source_id="source",
        source_name="notes.md",
        text=text,
        index=index,
    )


def test_terms_and_retrieval_support_utf8_without_external_index():
    assert "đăng" in terms("ĐĂNG nhập bằng JWT")
    chunks = make_chunks(
        "security.md",
        "Đăng nhập bằng JWT.\n\nDatabase dùng index cho truy vấn thường xuyên.",
        max_chars=20,
    )

    first = retrieve("đăng nhập JWT", chunks, top_k=2)
    second = retrieve("đăng nhập JWT", chunks, top_k=2)

    assert first
    assert [chunk.chunk_id for chunk in first] == [chunk.chunk_id for chunk in second]
    assert first[0].text == "Đăng nhập bằng JWT."
    assert retrieve("production region", chunks, top_k=2) == []


def test_retrieval_deduplicates_chunk_ids_and_orders_ties_deterministically():
    chunks = [
        _chunk("b", "JWT authorization", 1),
        _chunk("a", "JWT authentication", 0),
        _chunk("a", "JWT authentication duplicate", 0),
    ]

    results = retrieve("JWT", chunks, top_k=5)

    assert [chunk.chunk_id for chunk in results] == ["a", "b"]
    assert results[0].score == results[1].score


def test_token_budget_never_exceeds_hard_cap_when_truncating_first_chunk():
    selected, dropped = apply_token_budget([_chunk("long", "x" * 1000)], 7)

    assert selected
    assert sum(estimate_tokens(chunk.text) for chunk in selected) <= 7
    assert dropped == [
        {
            "chunk_id": "long",
            "reason": "truncated_to_hard_context_token_cap",
            "estimated_tokens": estimate_tokens("x" * 1000),
        }
    ]


def test_retrieval_and_budget_reject_invalid_limits():
    chunk = _chunk("c1", "local evidence")

    with pytest.raises(ValueError, match="top_k"):
        retrieve("evidence", [chunk], top_k=0)
    with pytest.raises(ValueError, match="max_tokens"):
        apply_token_budget([chunk], 0)


def test_citation_validation_is_limited_to_selected_evidence():
    available = [_chunk("c1", "first"), _chunk("c2", "second", 1)]

    valid, invalid = validate_citations(
        [" c2 ", "c1", "c2", "not-selected", "", "not-selected", 7],
        available,
    )

    assert valid == ["c2", "c1"]
    assert invalid == ["not-selected", "", "<int>"]
    assert validate_citations(["c1"], [_chunk("other", "not the packet")]) == (
        [],
        ["c1"],
    )
