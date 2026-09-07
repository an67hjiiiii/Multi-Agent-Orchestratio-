import asyncio
import os
from pathlib import Path
from app.research.pipeline import (
    TASK_QUERY_FALLBACK_REASON,
    TASK_QUERY_DOMAIN_FALLBACK_REASON,
    TASK_QUERY_FORMULATION_VERSION,
    ResearchPipeline,
    _build_task_retrieval_query,
    _task_relevance_terms,
    _retrieve_task_candidates,
)
from app.core.types import SourceChunk, Task
from app.research.context_controller import ContextController
from app.storage.source_store import SourceStore
from app.storage.run_store import RunStore


def test_a_b_c_fake_dev_profile(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "dev")
    sources=SourceStore(str(tmp_path/'data'))
    sources.import_text('security.md','Authentication uses bearer JWT. Authorization checks permissions server-side.')
    sources.import_text('db.md','Database queries should use indexes for frequent identifiers.')
    runs=RunStore(str(tmp_path/'runs'))
    pipe=ResearchPipeline(sources,runs)
    for condition in ['A','B','C','C-P','C-N','C-O']:
        run=asyncio.run(pipe.run('Review JWT security, database query and API architecture',condition,'fake'))
        assert run['condition']==condition
        assert run['answer']
        assert run['status'] != 'FAILED'
        assert run['metrics']['llm_calls']>=1
        assert runs.get(run['run_id']) is not None


def test_m0_rejects_non_a(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "m0")
    sources=SourceStore(str(tmp_path/'data'))
    runs=RunStore(str(tmp_path/'runs'))
    pipe=ResearchPipeline(sources,runs)
    try:
        asyncio.run(pipe.run('anything','B','fake'))
        assert False, 'B must be rejected in M0 profile'
    except ValueError as exc:
        assert 'not available in profile m0' in str(exc)


def test_m0_a_has_valid_citation_and_no_evidence_state(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "m0")
    sources=SourceStore(str(tmp_path/'data'))
    sources.import_text('api.md','The API contract defines request validation and error responses.')
    runs=RunStore(str(tmp_path/'runs'))
    pipe=ResearchPipeline(sources,runs)
    good=asyncio.run(pipe.run('What does the API contract define?','A','fake'))
    assert good['status']=='COMPLETE'
    assert good['task_results'][0]['citations']
    assert good['metrics']['citation_locator_validity']==1.0
    missing=asyncio.run(pipe.run('What is the production deployment region?','A','fake'))
    assert missing['status']=='NO_EVIDENCE'
    assert not missing['task_results'][0]['citations']


def test_task_retrieval_falls_back_to_user_request_only_after_task_query_miss():
    chunk = SourceChunk("db-1", "db", "db.md", "Queries need indexes for frequent identifiers.", 0)

    selected, reason = _retrieve_task_candidates(
        "Determine performance optimization candidates",
        "Which database queries need indexes?",
        [chunk],
        top_k=6,
        min_score=0.18,
    )

    assert [item.chunk_id for item in selected] == ["db-1"]
    assert reason == "task_query_no_results_fallback_to_user_request"


def test_task_retrieval_domain_anchor_avoids_wrong_domain_fallback():
    request = "Review the data model first, then check whether query access follows that model."
    task = Task(
        task_id="T1",
        goal="Review the data model to understand the database schema",
        domain="database",
    )
    database = SourceChunk(
        "database-1",
        "database",
        "database.md",
        "Database guidance: Queries that filter frequently used identifiers should be reviewed for appropriate indexes.",
        0,
    )
    security = SourceChunk(
        "security-1",
        "security",
        "security.md",
        "Authorization checks whether an authenticated user may access an action.",
        0,
    )

    task_query, _ = _build_task_retrieval_query(task, request)
    selected, reason = _retrieve_task_candidates(
        task_query,
        request,
        [database, security],
        top_k=6,
        min_score=0.18,
        task_domain=task.domain,
    )

    assert [chunk.chunk_id for chunk in selected] == ["database-1"]
    assert reason == TASK_QUERY_DOMAIN_FALLBACK_REASON


def test_task_retrieval_fallback_keeps_request_evidence_for_o_lite():
    request = "Review the service evidence and identify any missing SLA information."
    task = Task(task_id="T1", goal="Identify missing SLA information", domain="security")
    api = SourceChunk(
        "api-1",
        "api",
        "api.md",
        "The service exposes REST endpoints. This is the available service evidence.",
        0,
    )

    task_query, _ = _build_task_retrieval_query(task, request)
    candidates, reason = _retrieve_task_candidates(
        task_query,
        request,
        [api],
        top_k=6,
        min_score=0.18,
        task_domain=task.domain,
    )
    relevance_terms = _task_relevance_terms(task, task_query, request, reason)
    selected, dropped, _ = ContextController(max_tokens=100).select_for_task(
        candidates,
        task_terms=relevance_terms,
        max_tokens=100,
    )

    assert reason == TASK_QUERY_FALLBACK_REASON
    assert [chunk.chunk_id for chunk in selected] == ["api-1"]
    assert dropped == []


def test_task_query_preserves_request_anchors_without_noisy_paraphrase():
    task = Task(
        task_id="T1",
        goal="Identify specific authentication mechanisms and security protocols required for the system",
        domain="security",
    )

    retrieval_query, anchors = _build_task_retrieval_query(
        task,
        "Review authentication and database index requirements.",
    )

    assert anchors == ["authentication"]
    assert retrieval_query == "authentication"
    assert TASK_QUERY_FORMULATION_VERSION == "task-query-v2-anchor-preserving"
    assert TASK_QUERY_FALLBACK_REASON == "task_query_no_results_fallback_to_user_request"


def test_pipeline_records_anchor_query_version_and_fallback_reason(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "dev")
    sources = SourceStore(str(tmp_path / "data"))
    sources.import_text("db.md", "Queries need indexes for frequent identifiers.")
    run = asyncio.run(
        ResearchPipeline(sources, RunStore(str(tmp_path / "runs"))).run(
            "Review authentication and database index requirements.", "B", "fake"
        )
    )

    retrieval_events = [
        event for event in run["events"] if event["stage"] == "task_retrieval"
    ]
    assert retrieval_events
    assert all(
        event["task_query_version"] == TASK_QUERY_FORMULATION_VERSION
        for event in retrieval_events
    )
    assert any(
        event["retrieval_fallback_reason"] == TASK_QUERY_FALLBACK_REASON
        for event in retrieval_events
    )


def test_failed_decomposition_is_explicit_not_an_empty_partial(tmp_path: Path, monkeypatch):
    from app.research import pipeline as pipeline_module
    from app.research.task_schema import DecompositionResult

    async def failed_decompose(*_args):
        return DecompositionResult(
            request="Review authentication",
            tasks=[],
            planning_evidence_ids=[],
            status="FAILED",
            warnings=["invalid task schema"],
        )

    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "dev")
    monkeypatch.setattr(pipeline_module, "decompose", failed_decompose)
    run = asyncio.run(ResearchPipeline(SourceStore(str(tmp_path / "data")), RunStore(str(tmp_path / "runs"))).run(
        "Review authentication", "B", "fake"
    ))

    assert run["status"] == "FAILED"
    assert run["tasks"] == []
    assert any(event["stage"] == "decomposition_failed" for event in run["events"])
