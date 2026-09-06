from __future__ import annotations

import pytest

from app.research.planning_retrieval import (
    PlanningKnowledgeItem,
    PlanningRetriever,
)
from app.retrieval.text import estimate_tokens


def _items() -> list[PlanningKnowledgeItem]:
    return [
        PlanningKnowledgeItem(
            id="plan-security",
            domain="security",
            title="Separate authentication and authorization",
            content="Keep identity verification and permission checks as separate atomic tasks.",
            provenance="planning-kb:v1/security",
        ),
        PlanningKnowledgeItem(
            id="plan-api",
            domain="api_architecture",
            title="Preserve API dependencies",
            content="Keep endpoint contracts, errors, and integration dependencies explicit.",
            provenance="planning-kb:v1/api",
        ),
    ]


def test_retrieval_returns_planning_items_not_answer_chunks():
    result = PlanningRetriever(items=_items()).retrieve(
        "Review authentication and authorization",
        include_scores=True,
    )

    assert result.item_ids == ["plan-security"]
    assert result.scores is not None
    assert len(result.scores) == len(result.item_ids)
    assert "Separate authentication" in result.context
    assert "planning-kb:v1/security" in result.context


def test_scores_are_hidden_by_default_and_can_be_exposed_explicitly():
    retriever = PlanningRetriever(items=_items())

    hidden = retriever.retrieve("API endpoint errors")
    exposed = retriever.retrieve("API endpoint errors", expose_scores=True)

    assert hidden.scores is None
    assert exposed.scores is not None
    assert len(exposed.scores) == len(exposed.item_ids)
    assert all(0.0 <= score <= 1.0 for score in exposed.scores)


def test_relevance_gate_has_explicit_empty_result_without_fallback():
    result = PlanningRetriever(items=_items()).retrieve(
        "What is the production deployment region?",
        include_scores=True,
    )

    assert result.item_ids == []
    assert result.scores == []
    assert result.context == ""
    assert list(result) == []


def test_context_is_hard_bounded_and_legacy_search_is_iterable():
    items = [
        PlanningKnowledgeItem(
            id="plan-long",
            domain="security",
            title="Security planning guidance",
            content="security " * 600,
            provenance="planning-kb:v1/long",
        ),
        _items()[1],
    ]
    retriever = PlanningRetriever(
        items=items,
        max_context_tokens=40,
        expose_scores=True,
    )

    result = retriever.search("security planning guidance", top_k=2)

    assert estimate_tokens(result.context) <= 40
    assert result.item_ids == ["plan-long"]
    assert result.scores is not None
    assert [hit.chunk_id for hit in result] == result.item_ids
    assert result[0].text


def test_malformed_planning_item_is_rejected():
    with pytest.raises(ValueError, match="provenance"):
        PlanningRetriever(
            items=[
                {
                    "id": "plan-bad",
                    "domain": "security",
                    "title": "Bad item",
                    "content": "content",
                    "provenance": "",
                }
            ]
        )
