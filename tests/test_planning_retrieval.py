from __future__ import annotations

import pytest

from app.research.planning_retrieval import (
    PlanningKnowledgeItem,
    PlanningRetriever,
    PLANNING_RETRIEVAL_SCORING_VERSION,
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


def _domain_items() -> list[PlanningKnowledgeItem]:
    return [
        PlanningKnowledgeItem(
            id="plan-security",
            domain="security",
            title="Keep distinct security obligations atomic",
            content="Keep authentication and authorization as separate planning obligations.",
            provenance="planning-kb:v1/security",
        ),
        PlanningKnowledgeItem(
            id="plan-database",
            domain="database",
            title="Split database review concerns",
            content="Keep transaction and consistency obligations in database planning.",
            provenance="planning-kb:v1/database",
        ),
        PlanningKnowledgeItem(
            id="plan-api",
            domain="api_architecture",
            title="Preserve API boundaries and dependencies",
            content="Keep API endpoint contracts, errors, and integration dependencies explicit.",
            provenance="planning-kb:v1/api",
        ),
        PlanningKnowledgeItem(
            id="plan-multi",
            domain="multi_domain",
            title="Plan independent obligations",
            content="Create one planning task per independent requested obligation.",
            provenance="planning-kb:v1/multi-domain",
        ),
    ]


def test_scoring_version_is_explicit_and_traceable():
    assert PLANNING_RETRIEVAL_SCORING_VERSION == "idf-content-anchor-v1"


def test_content_anchor_rejects_unrelated_api_boundary_for_transaction_request():
    result = PlanningRetriever(
        items=_domain_items(),
        expose_scores=True,
    ).retrieve("When are transaction boundaries required?")

    assert result.item_ids == ["plan-database"]
    assert result.scores is not None
    assert result.scores[0] >= 0.18


def test_multi_domain_request_keeps_each_relevant_domain_pattern():
    result = PlanningRetriever(
        items=_domain_items(),
        expose_scores=True,
    ).retrieve("Review authentication and database index requirements.")

    assert result.item_ids[:2] == ["plan-database", "plan-security"]
    assert "plan-api" not in result.item_ids


def test_unrepresented_detail_does_not_dilute_known_multi_domain_anchors():
    result = PlanningRetriever(
        items=_domain_items(),
        expose_scores=True,
    ).retrieve("Review JWT policy database transactions and API authorization.")

    assert result.item_ids[0] == "plan-database"
    assert set(result.item_ids) == {"plan-database", "plan-api", "plan-security"}


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
