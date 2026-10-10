import asyncio
import json

from app.core.types import ProviderResult, RunMetrics, SourceChunk, Task, TaskResult, Usage
from app.research.synthesizer import synthesize
from app.research.worker import execute_task


class StubProvider:
    model = "stub"

    def __init__(self, payload: object):
        self.payload = payload
        self.system = ""
        self.user = ""

    async def generate(self, *, system: str, user: str) -> ProviderResult:
        self.system, self.user = system, user
        text = self.payload if isinstance(self.payload, str) else json.dumps(self.payload)
        return ProviderResult(text=text, usage=Usage(1, 1), model=self.model)


def _task() -> Task:
    return Task(task_id="T1", goal="Review API validation", domain="api_architecture")


def _evidence() -> list[SourceChunk]:
    return [SourceChunk("chunk-1", "source-1", "api.md", "The API validates requests.", 0)]


def test_worker_maps_evidence_key_to_canonical_chunk_id():
    provider = StubProvider({"status": "COMPLETE", "answer": "supported", "citations": ["E1"], "missing_information": []})

    result = asyncio.run(execute_task(provider, _task(), _evidence(), RunMetrics()))

    assert "[E1] [chunk-1]" in provider.user
    assert '"citations":["E1"]' in provider.user
    assert result.status == "COMPLETE"
    assert result.citations == ["chunk-1"]
    assert result.invalid_citations == []


def test_worker_rejects_unselected_evidence_key_and_no_evidence_is_citation_free():
    provider = StubProvider({"status": "COMPLETE", "answer": "unsupported", "citations": ["E2"], "missing_information": []})

    invalid = asyncio.run(execute_task(provider, _task(), _evidence(), RunMetrics()))
    empty = asyncio.run(execute_task(provider, _task(), [], RunMetrics()))

    assert invalid.status == "PARTIAL"
    assert invalid.citations == []
    assert invalid.invalid_citations == ["E2"]
    assert empty.status == "NO_EVIDENCE"
    assert empty.citations == []


def test_worker_partial_without_missing_information_has_deterministic_reason():
    provider = StubProvider({"status": "PARTIAL", "answer": "bounded answer", "citations": ["E1"], "missing_information": []})

    result = asyncio.run(execute_task(provider, _task(), _evidence(), RunMetrics()))

    assert result.status == "PARTIAL"
    assert result.missing_information == []
    assert result.status_reason == "WORKER_PARTIAL_WITHOUT_REASON"


def test_worker_rejects_status_outside_worker_contract():
    provider = StubProvider(
        {
            "status": "FAILED",
            "answer": "The worker cannot set the run terminal status.",
            "citations": ["E1"],
            "missing_information": [],
        }
    )

    result = asyncio.run(execute_task(provider, _task(), _evidence(), RunMetrics()))

    assert result.status == "PARTIAL"
    assert result.status_reason == "INVALID_WORKER_STATUS"
    assert result.missing_information == ["invalid worker status"]


def test_synthesizer_preserves_multiple_task_citations():
    provider = StubProvider({"answer": "Combined answer", "citations": ["E1", "E2"]})
    results = [
        TaskResult("T1", "security", "COMPLETE", "auth", evidence_ids=["chunk-1"], citations=["chunk-1"]),
        TaskResult("T2", "api_architecture", "COMPLETE", "api", evidence_ids=["chunk-2"], citations=["chunk-2"]),
    ]

    answer = asyncio.run(synthesize(provider, "Review both", results, RunMetrics()))

    assert "[chunk-1]" in answer
    assert "[chunk-2]" in answer


def test_synthesizer_maps_keys_against_deduplicated_evidence_order():
    provider = StubProvider({
        "answer": "This is a sufficiently long combined answer.",
        "citations": ["E3"],
    })
    results = [
        TaskResult("T1", "domain", "COMPLETE", "one", evidence_ids=["c1"]),
        TaskResult("T2", "domain", "COMPLETE", "two", evidence_ids=["c2"]),
        TaskResult("T3", "domain", "COMPLETE", "three", evidence_ids=["c2"]),
        TaskResult("T4", "domain", "COMPLETE", "four", evidence_ids=["c3"]),
    ]

    answer = asyncio.run(synthesize(provider, "Review all", results, RunMetrics()))

    assert "E3=c3" in provider.user
    assert "[c3]" in answer
    assert "[c2]" not in answer


def test_synthesis_drops_malformed_or_unselected_locator_from_final_answer():
    provider = StubProvider({"answer": "Combined", "citations": ["chunk-1:0000", "E2"]})
    results = [TaskResult("T1", "security", "COMPLETE", "auth", evidence_ids=["chunk-1"], citations=["chunk-1"])]

    answer = asyncio.run(synthesize(provider, "Review", results, RunMetrics()))

    assert "[chunk-1]" in answer
    assert "chunk-1:0000" not in answer
    assert "E2" not in answer


def test_synthesis_no_evidence_stays_citation_free():
    provider = StubProvider({"answer": "No evidence", "citations": ["E1"]})
    results = [TaskResult("T1", "security", "NO_EVIDENCE", "No evidence")]

    answer = asyncio.run(synthesize(provider, "Review", results, RunMetrics()))

    assert "Nguồn:" not in answer


def test_synthesis_uses_question_first_fallback_for_thin_model_answer():
    provider = StubProvider({"answer": "yes", "citations": ["E1"]})
    results = [
        TaskResult(
            "T1",
            "security",
            "COMPLETE",
            "Authentication verifies identity.",
            evidence_ids=["chunk-1"],
            citations=["chunk-1"],
        )
    ]

    answer = asyncio.run(synthesize(provider, "How does authentication work?", results, RunMetrics()))

    assert answer.startswith("Kết luận:")
    assert "Authentication verifies identity." in answer
    assert "[chunk-1]" in answer
