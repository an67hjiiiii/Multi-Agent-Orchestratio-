from app.research.planning_retrieval import (
    PLANNING_RELEVANCE_THRESHOLD,
    PlanningRetriever,
)


def test_planning_search_returns_relevance_ranked_matches_with_top_k_cap():
    hits = PlanningRetriever().search(
        "Review authentication authorization obligations", top_k=2
    )

    assert [hit.source_name for hit in hits] == [
        "planning_security.md",
        "planning_multi_domain.md",
    ]
    assert all(hit.score >= PLANNING_RELEVANCE_THRESHOLD for hit in hits)
    assert hits[0].score >= hits[1].score


def test_planning_search_does_not_fallback_to_unrelated_patterns():
    hits = PlanningRetriever().search(
        "What is the production deployment region?", top_k=3
    )

    assert hits == []


def test_planning_search_filters_low_relevance_matches_before_top_k():
    hits = PlanningRetriever().search(
        "Review database query performance and API endpoints", top_k=4
    )

    assert [hit.source_name for hit in hits] == [
        "planning_database.md",
        "planning_api.md",
    ]
    assert all(hit.score >= PLANNING_RELEVANCE_THRESHOLD for hit in hits)
