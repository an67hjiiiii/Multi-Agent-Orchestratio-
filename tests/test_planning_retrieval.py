from app.research.planning_retrieval import (
    PlanningRetriever,
)


def test_planning_search_returns_relevance_ranked_matches_with_top_k_cap():
    hits = PlanningRetriever().search(
        "Review authentication authorization", top_k=1
    )

    assert [hit.source_name for hit in hits] == [
        "planning_security.md",
    ]
    assert hits[0].score > 0


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


def test_planning_search_api_only_query_returns_only_api_evidence():
    hits = PlanningRetriever().search("Review API error handling", top_k=4)

    assert [hit.source_name for hit in hits] == ["planning_api.md"]


def test_planning_search_security_and_access_control_returns_security_evidence():
    hits = PlanningRetriever().search("security access-control", top_k=4)

    assert [hit.source_name for hit in hits] == ["planning_security.md"]


def test_planning_search_database_access_returns_database_evidence():
    hits = PlanningRetriever().search("database access", top_k=4)

    assert [hit.source_name for hit in hits] == ["planning_database.md"]


def test_planning_search_data_model_returns_database_evidence():
    hits = PlanningRetriever().search("data model", top_k=4)

    assert [hit.source_name for hit in hits] == ["planning_database.md"]


def test_planning_search_generic_only_query_returns_no_evidence():
    assert PlanningRetriever().search("Review request", top_k=4) == []


def test_planning_search_uses_configurable_min_score():
    query = "API"
    low_floor = PlanningRetriever(min_score=0.0).search(query)
    assert [hit.source_name for hit in low_floor] == ["planning_api.md"]

    high_floor = PlanningRetriever(min_score=low_floor[0].score + 0.01).search(query)
    assert high_floor == []


def test_long_planning_request_keeps_domain_intent_above_existing_floor():
    query = (
        "Review the uploaded architecture, database and security design. "
        "Identify the important technical obligations and explicit concerns, "
        "determine their domains and dependencies, retrieve supporting planning "
        "evidence, and produce a validated implementation plan. "
        "Do not silently omit any identified requirement."
    )
    hits = PlanningRetriever(min_score=0.18).search(query)
    assert {hit.source_name for hit in hits} == {
        "planning_api.md", "planning_database.md", "planning_security.md"
    }
    assert all(hit.score >= 0.18 for hit in hits)
    assert PlanningRetriever(min_score=0.18).search(
        "Identify important obligations, retrieve evidence and produce a plan for a recipe."
    ) == []
