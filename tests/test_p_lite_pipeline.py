import asyncio

import pytest

from app.core.types import RunMetrics, SourceChunk, Task, Usage
from app.providers.fake import FakeProvider
from app.research.p_lite_pipeline import PLitePipeline
from app.retrieval.text import estimate_tokens


class RecordingRetriever:
    def __init__(self, items):
        self.items = items
        self.calls = []

    def search(self, query, top_k=3):
        self.calls.append((query, top_k))
        return self.items


class ValidDecomposer:
    def __init__(self):
        self.contexts = []

    async def __call__(self, provider, query, planning_context, metrics):
        self.contexts.append(planning_context)
        metrics.add_usage(Usage(input_tokens=9, output_tokens=5))
        return [
            Task("T1", "Review authentication", "security"),
            Task("T2", "Review the API contract", "api_architecture", depends_on=["T1"]),
        ]


def _source_chunk(chunk_id, text, score):
    return SourceChunk(
        chunk_id=chunk_id,
        source_id="planning-source",
        source_name="planning.md",
        text=text,
        index=0,
        score=score,
    )


def test_p_lite_bounds_planning_context_and_records_telemetry():
    retriever = RecordingRetriever(
        [
            _source_chunk("P1", "Authentication and authorization planning guidance " * 8, 0.9),
            _source_chunk("P2", "API contract planning guidance " * 8, 0.8),
            _source_chunk("P3", "Unselected planning guidance", 0.1),
        ]
    )
    decomposer = ValidDecomposer()
    metrics = RunMetrics()
    pipeline = PLitePipeline(
        planning_retriever=retriever,
        decomposer=decomposer,
        planning_top_k=3,
        max_items=2,
        max_context_tokens=30,
    )

    result = asyncio.run(pipeline.run("Review authentication and API", FakeProvider(), metrics))

    assert result.status == "COMPLETE"
    assert len(result.planning_evidence_ids) <= 2
    assert estimate_tokens(result.planning_context) <= 30
    assert decomposer.contexts == [result.planning_context]
    assert retriever.calls == [("Review authentication and API", 3)]
    assert result.llm_calls == 1
    assert metrics.input_tokens == 9
    assert metrics.output_tokens == 5
    assert result.latency_ms >= 0
    assert result.to_dict()["planning"]["item_ids"] == result.planning_evidence_ids
    assert result.planning.snapshot_id.startswith("planning_")
    assert result.planning.selected_item_ids == result.planning_evidence_ids
    assert result.planning.dropped_item_ids == ["P2", "P3"]


class RepairingDecomposer:
    def __init__(self):
        self.calls = 0

    async def __call__(self, provider, query, planning_context, metrics):
        self.calls += 1
        metrics.add_usage(Usage(input_tokens=2, output_tokens=2))
        if self.calls == 1:
            return [Task("T1", "Invalid first attempt", depends_on=["MISSING"])]
        return [Task("T1", "First task"), Task("T2", "Second task", depends_on=["T1"])]


def test_p_lite_uses_at_most_one_structured_retry_for_invalid_dependencies():
    decomposer = RepairingDecomposer()
    pipeline = PLitePipeline(
        planning_retriever=RecordingRetriever([]),
        decomposer=decomposer,
        retry_limit=1,
    )

    result = asyncio.run(pipeline.run("Split the request", FakeProvider()))

    assert result.status == "COMPLETE"
    assert [task.task_id for task in result.tasks] == ["T1", "T2"]
    assert decomposer.calls == 2
    assert result.llm_calls == 2
    assert "structured decomposition retry used" in result.warnings


class CyclicDecomposer:
    def __init__(self):
        self.calls = 0

    async def __call__(self, provider, query, planning_context, metrics):
        self.calls += 1
        metrics.add_usage(Usage())
        return [
            Task("T1", "First task", depends_on=["T2"]),
            Task("T2", "Second task", depends_on=["T1"]),
        ]


def test_p_lite_returns_explicit_failure_after_retry_budget_is_exhausted():
    decomposer = CyclicDecomposer()
    pipeline = PLitePipeline(
        planning_retriever=RecordingRetriever([]),
        decomposer=decomposer,
        retry_limit=1,
    )

    result = asyncio.run(pipeline.run("Split the request", FakeProvider()))

    assert result.status == "FAILED"
    assert result.tasks == []
    assert decomposer.calls == 2
    assert result.llm_calls == 2
    assert any("decomposition validation failed" in warning for warning in result.warnings)


def test_p_lite_does_not_add_a_wrapper_retry_to_the_default_decomposer(monkeypatch):
    from app.research import p_lite_pipeline
    from app.research.task_schema import DecompositionResult

    calls = 0

    async def failed_default(*_args):
        nonlocal calls
        calls += 1
        return DecompositionResult(
            request="Split the request",
            tasks=[],
            planning_evidence_ids=[],
            status="FAILED",
            warnings=["structured output remained invalid"],
        )

    monkeypatch.setattr(p_lite_pipeline, "default_decompose", failed_default)
    pipeline = p_lite_pipeline.PLitePipeline(planning_retriever=RecordingRetriever([]))

    result = asyncio.run(pipeline.run("Split the request", FakeProvider()))

    assert result.status == "FAILED"
    assert calls == 1


async def _contract_decomposer(provider, request, planning_context, metrics):
    assert planning_context == ""
    metrics.add_usage(Usage(input_tokens=3, output_tokens=2))
    return {
        "status": "COMPLETE",
        "tasks": [
            {
                "task_id": "T1",
                "title": "Inspect the request",
                "objective": request,
                "expected_output": "A task inspection",
                "domain": "general",
                "role_profile": "reviewer",
                "depends_on": [],
            }
        ],
    }


def test_p_lite_accepts_the_locked_task_shape_and_named_decomposer_inputs():
    pipeline = PLitePipeline(
        planning_retriever=RecordingRetriever([]),
        decomposer=_contract_decomposer,
    )

    result = asyncio.run(pipeline.run("Inspect this request", FakeProvider()))

    assert result.status == "COMPLETE"
    assert result.tasks[0]["task_id"] == "T1"
    assert result.llm_calls == 1
    assert result.metrics.latency_ms == result.latency_ms


def test_p_lite_rejects_non_local_provider_names():
    pipeline = PLitePipeline(planning_retriever=RecordingRetriever([]))

    with pytest.raises(ValueError, match="fake and local Ollama"):
        asyncio.run(pipeline.run("Split the request", "openai"))


def test_p_lite_resolves_an_explicit_local_provider_name():
    pipeline = PLitePipeline(
        planning_retriever=RecordingRetriever([]),
        decomposer=_contract_decomposer,
    )

    result = asyncio.run(pipeline.run("Inspect this request", "fake"))

    assert result.status == "COMPLETE"


def test_p_lite_serializes_canonical_pydantic_tasks():
    from app.research.task_schema import TaskItem

    pipeline = PLitePipeline(
        planning_retriever=RecordingRetriever([]),
        decomposer=lambda *_args: [
            TaskItem(
                task_id="T1",
                title="Inspect the contract",
                objective="Validate the task schema.",
                expected_output="Inspection result",
                domain="api_architecture",
                role_profile="reviewer",
                depends_on=[],
            )
        ],
    )

    payload = asyncio.run(pipeline.run("Inspect this request", FakeProvider())).to_dict()

    assert payload["tasks"] == [{
        "task_id": "T1",
        "title": "Inspect the contract",
        "objective": "Validate the task schema.",
        "expected_output": "Inspection result",
        "domain": "api_architecture",
        "role_profile": "reviewer",
        "depends_on": [],
    }]


def test_p_lite_off_skips_retrieval_and_logs_fallback_flag():
    retriever = RecordingRetriever([_source_chunk("P1", "unused", 1.0)])
    pipeline = PLitePipeline(planning_retriever=retriever, decomposer=_contract_decomposer, planning_enabled=False)
    result = asyncio.run(pipeline.run("Inspect this request", FakeProvider()))
    assert result.status == "COMPLETE"
    assert retriever.calls == []
    assert result.planning.enabled is False
    assert result.planning.fallback_reason == "P_DISABLED"
    assert result.planning_context == ""


def test_p_lite_relevance_fallback_is_explicit():
    pipeline = PLitePipeline(planning_retriever=RecordingRetriever([]), decomposer=_contract_decomposer)
    result = asyncio.run(pipeline.run("Inspect this request", FakeProvider()))
    assert result.planning.enabled is True
    assert result.planning.fallback_reason == "NO_RELEVANT_PLANNING_EVIDENCE"
