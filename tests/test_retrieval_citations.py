from __future__ import annotations

import asyncio

import pytest

from app.core.citations import resolve_citations, validate_citations
from app.core.types import ProviderResult, RunMetrics, SourceChunk, Usage
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


def test_evidence_key_resolves_to_canonical_locator():
    chunk = _chunk("src_0123456789abcdef_c0000", "first")

    assert resolve_citations(["E1"], [chunk]) == (
        [chunk.chunk_id],
        [],
    )


def test_malformed_and_truncated_locators_are_rejected():
    chunk = _chunk("src_0123456789abcdef_c0000", "first")

    assert resolve_citations(
        ["src_0123456789abc:0000", "src_0123456789abcdef_c00", "E2"],
        [chunk],
    ) == (
        [],
        ["src_0123456789abc:0000", "src_0123456789abcdef_c00", "E2"],
    )


def test_vanilla_answer_maps_key_and_keeps_invalid_citation_out():
    chunk = _chunk("src_0123456789abcdef_c0000", "first")

    class Provider:
        model = "test"

        async def generate(self, *, system: str, user: str) -> ProviderResult:
            assert "[E1]" in user
            assert f"[{chunk.chunk_id}]" in user
            assert '"citations":["evidence_key"]' in system
            return ProviderResult(
                text='{"status":"COMPLETE","answer":"supported","citations":["E1"],"missing_information":[]}',
                usage=Usage(1, 1),
                model=self.model,
            )

    from app.research.vanilla import answer_vanilla

    result = asyncio.run(answer_vanilla(Provider(), "question", [chunk], RunMetrics()))

    assert result.status == "COMPLETE"
    assert result.citations == [chunk.chunk_id]
    assert result.invalid_citations == []
    assert chunk.chunk_id in result.answer


def test_vanilla_no_evidence_remains_citation_free():
    class UnexpectedProvider:
        async def generate(self, **_kwargs):
            raise AssertionError("NO_EVIDENCE must not call the provider")

    from app.research.vanilla import answer_vanilla

    result = asyncio.run(answer_vanilla(UnexpectedProvider(), "question", [], RunMetrics()))

    assert result.status == "NO_EVIDENCE"
    assert result.citations == []
    assert result.invalid_citations == []
