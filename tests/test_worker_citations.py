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


def test_synthesizer_preserves_multiple_task_citations():
    provider = StubProvider("Combined answer")
    results = [
        TaskResult("T1", "security", "COMPLETE", "auth", citations=["chunk-1"]),
        TaskResult("T2", "api_architecture", "COMPLETE", "api", citations=["chunk-2"]),
    ]

    answer = asyncio.run(synthesize(provider, "Review both", results, RunMetrics()))

    assert "[chunk-1]" in answer
    assert "[chunk-2]" in answer
