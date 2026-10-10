import asyncio

from app.core.types import RunMetrics, SourceChunk, Task
from app.providers.fake import FakeProvider
from app.research.worker import execute_task


def test_worker_returns_no_evidence_without_calling_provider():
    metrics = RunMetrics()
    result = asyncio.run(
        execute_task(
            FakeProvider(),
            Task(task_id="T1", goal="Review account security", domain="security"),
            [],
            metrics,
        )
    )

    assert result.status == "NO_EVIDENCE"
    assert result.evidence_ids == []
    assert result.citations == []
    assert result.missing_information == ["relevant evidence"]
    assert metrics.llm_calls == 0


def test_worker_returns_grounded_complete_result_for_supplied_evidence():
    chunk_id = "src_0123456789abcdef_c0000"
    evidence = [
        SourceChunk(
            chunk_id=chunk_id,
            source_id="src_0123456789abcdef",
            source_name="security.md",
            text="Authentication verifies identity.",
            index=0,
        )
    ]
    metrics = RunMetrics()
    result = asyncio.run(
        execute_task(
            FakeProvider(),
            Task(task_id="T1", goal="Review identity", domain="security"),
            evidence,
            metrics,
        )
    )

    assert result.status == "COMPLETE"
    assert result.evidence_ids == [chunk_id]
    assert result.citations == [chunk_id]
    assert result.invalid_citations == []
    assert metrics.llm_calls == 1
    assert metrics.citations_valid == 1
