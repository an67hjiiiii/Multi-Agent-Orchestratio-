import asyncio
from pathlib import Path

from app.core.types import SourceChunk
from app.research.context_controller import ContextController
from app.research.pipeline import (
    DOMAIN_RANKING_VERSION,
    RETRIEVAL_SCORING_VERSION,
    SCORING_VERSION_METADATA,
    ResearchPipeline,
)
from app.research.planning_retrieval import PLANNING_RETRIEVAL_SCORING_VERSION
from app.retrieval.text import (
    apply_token_budget,
    domain_compatibility,
    estimate_context_tokens,
    lexical_score,
    retrieve,
)
from app.storage.run_store import RunStore
from app.storage.source_store import SourceStore


def _chunk(
    chunk_id: str,
    source_id: str,
    source_name: str,
    text: str,
    index: int = 0,
    score: float = 0.0,
) -> SourceChunk:
    return SourceChunk(chunk_id, source_id, source_name, text, index, score)


def test_retrieval_prefers_canonical_domain_metadata_before_top_k_cut():
    compatible = _chunk(
        "database-compatible",
        "database-source",
        "database.md",
        "Requirements should be documented for data access.",
    )
    incompatible = _chunk(
        "security-compatible",
        "security-source",
        "security.md",
        "Requirements should be documented with authorization policy.",
    )

    result = retrieve(
        "requirements documented",
        [incompatible, compatible],
        top_k=1,
        task_domain="database",
    )

    assert [chunk.chunk_id for chunk in result] == [compatible.chunk_id]
    assert result[0].score == lexical_score("requirements documented", compatible)
    assert domain_compatibility(compatible, "database") == 2
    assert domain_compatibility(incompatible, "database") == 0


def test_domain_ranking_keeps_shared_evidence_and_unlabelled_candidates():
    shared = _chunk(
        "shared-evidence",
        "shared-source",
        "notes.md",
        "API authorization requirements and database consistency are documented.",
    )
    unlabelled = _chunk(
        "unlabelled-evidence",
        "unlabelled-source",
        "notes.md",
        "Requirements should be documented.",
    )

    assert domain_compatibility(shared, "security") > 0
    assert domain_compatibility(shared, "database") > 0
    assert [chunk.chunk_id for chunk in retrieve(
        "authorization requirements",
        [shared],
        task_domain="security",
    )] == [shared.chunk_id]
    assert [chunk.chunk_id for chunk in retrieve(
        "requirements documented",
        [unlabelled],
        task_domain="database",
    )] == [unlabelled.chunk_id]


def test_pipeline_and_o_lite_share_context_token_estimation():
    chunks = [
        _chunk("first", "source", "notes.md", "a" * 15, score=1.0),
        _chunk("second", "source", "notes.md", "b" * 15, score=0.9),
        _chunk("third", "source", "notes.md", "c" * 15, score=0.8),
    ]

    pipeline_selected, _ = apply_token_budget(chunks, 10)
    controller_selected, _ = ContextController(max_tokens=10).select(chunks)

    assert [chunk.chunk_id for chunk in pipeline_selected] == ["first", "second"]
    assert [chunk.chunk_id for chunk in controller_selected] == ["first", "second"]
    assert estimate_context_tokens(pipeline_selected) == estimate_context_tokens(
        controller_selected
    ) == 10


def test_pipeline_persists_scoring_versions_in_run_and_trace(
    tmp_path: Path, monkeypatch
):
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "dev")
    sources = SourceStore(str(tmp_path / "data"))
    sources.import_text("api.md", "The API contract defines request validation.")
    runs = RunStore(str(tmp_path / "runs"))

    vanilla = asyncio.run(
        ResearchPipeline(sources, runs).run(
            "What does the API contract define?", "A", "fake"
        )
    )

    assert vanilla["scoring_versions"] == SCORING_VERSION_METADATA
    assert vanilla["effective_config"]["scoring_versions"] == SCORING_VERSION_METADATA
    assert vanilla["planning_retrieval_scoring_version"] == PLANNING_RETRIEVAL_SCORING_VERSION
    assert vanilla["retrieval_scoring_version"] == RETRIEVAL_SCORING_VERSION
    assert vanilla["domain_ranking_version"] == DOMAIN_RANKING_VERSION
    assert vanilla["events"][0]["scoring_versions"] == SCORING_VERSION_METADATA
    retrieval_event = next(
        event for event in vanilla["events"] if event["stage"] == "vanilla_retrieval"
    )
    assert retrieval_event["scoring_version"] == RETRIEVAL_SCORING_VERSION

    planned = asyncio.run(
        ResearchPipeline(sources, runs).run("Review authentication", "C", "fake")
    )
    planning_event = next(
        event for event in planned["events"] if event["stage"] == "planning_retrieval"
    )
    assert planning_event["scoring_version"] == PLANNING_RETRIEVAL_SCORING_VERSION
