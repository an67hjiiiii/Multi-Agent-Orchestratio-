import asyncio
import json

from app.core.types import ProviderResult, RunMetrics, SourceChunk, Usage
from app.research.vanilla import answer_vanilla


class StubProvider:
    name = "stub"
    model = "stub-m0"

    def __init__(self, response: object):
        self.response = response
        self.calls = 0
        self.system = ""
        self.user = ""

    async def generate(self, *, system: str, user: str) -> ProviderResult:
        self.calls += 1
        self.system = system
        self.user = user
        text = self.response if isinstance(self.response, str) else json.dumps(self.response)
        return ProviderResult(text=text, usage=Usage(input_tokens=11, output_tokens=7))


def _evidence() -> list[SourceChunk]:
    return [
        SourceChunk("chunk-1", "source-1", "api.md", "The API validates requests.", 0),
        SourceChunk("chunk-2", "source-1", "api.md", "The API returns structured errors.", 1),
    ]


def _answer(provider: StubProvider, evidence: list[SourceChunk] | None = None) -> tuple[object, RunMetrics]:
    metrics = RunMetrics()
    selected_evidence = _evidence() if evidence is None else evidence
    result = asyncio.run(answer_vanilla(provider, "What does the API define?", selected_evidence, metrics))
    return result, metrics


def test_no_evidence_is_terminal_and_does_not_call_provider():
    provider = StubProvider({"status": "COMPLETE", "answer": "should not run", "citations": ["chunk-1"]})
    result, metrics = _answer(provider, evidence=[])

    assert result.status == "NO_EVIDENCE"
    assert result.answer == "Không tìm thấy bằng chứng phù hợp trong nguồn đã nạp để trả lời yêu cầu này."
    assert result.evidence_ids == []
    assert result.citations == []
    assert result.missing_information == ["relevant evidence"]
    assert provider.calls == 0
    assert metrics.llm_calls == 0


def test_complete_answer_has_grounded_schema_and_deduplicated_valid_citations():
    provider = StubProvider(
        {
            "status": "complete",
            "answer": "The contract validates requests and returns structured errors.",
            "citations": [" chunk-2", "chunk-1", "chunk-2"],
            "missing_information": [],
        }
    )
    result, metrics = _answer(provider)

    assert result.status == "COMPLETE"
    assert result.citations == ["chunk-2", "chunk-1"]
    assert result.invalid_citations == []
    assert result.evidence_ids == ["chunk-1", "chunk-2"]
    assert "Nguồn: [chunk-2], [chunk-1]" in result.answer
    assert metrics.llm_calls == 1
    assert metrics.input_tokens == 11
    assert metrics.output_tokens == 7
    assert metrics.citations_emitted == 2
    assert metrics.to_dict()["citation_locator_validity"] == 1.0
    assert "VANILLA_RAG_ANSWERER" in provider.system
    assert "[chunk-1]" in provider.user and "[chunk-2]" in provider.user


def test_invalid_citations_are_removed_and_complete_is_downgraded_to_partial():
    provider = StubProvider(
        {
            "status": "COMPLETE",
            "answer": "The request is validated.",
            "citations": ["chunk-1", "made-up-chunk"],
            "missing_information": [],
        }
    )
    result, metrics = _answer(provider)

    assert result.status == "PARTIAL"
    assert result.citations == ["chunk-1"]
    assert result.invalid_citations == ["made-up-chunk"]
    assert "[chunk-1]" in result.answer
    assert "made-up-chunk" not in result.answer
    assert "invalid citation locator(s) removed" in result.missing_information
    assert metrics.citations_emitted == 2
    assert metrics.citations_valid == 1
    assert metrics.to_dict()["citation_locator_validity"] == 0.5


def test_complete_without_a_valid_citation_is_partial():
    provider = StubProvider(
        {
            "status": "COMPLETE",
            "answer": "The contract defines request validation.",
            "citations": [],
            "missing_information": [],
        }
    )
    result, _ = _answer(provider)

    assert result.status == "PARTIAL"
    assert result.citations == []
    assert "answer has no valid citation" in result.missing_information


def test_provider_no_evidence_is_preserved_as_a_terminal_state():
    provider = StubProvider(
        {
            "status": "NO_EVIDENCE",
            "answer": "",
            "citations": [],
            "missing_information": [],
        }
    )
    result, metrics = _answer(provider)

    assert result.status == "NO_EVIDENCE"
    assert result.answer == "Không tìm thấy bằng chứng phù hợp trong nguồn đã nạp để trả lời yêu cầu này."
    assert result.citations == []
    assert result.missing_information == ["relevant evidence"]
    assert provider.calls == 1
    assert metrics.llm_calls == 1


def test_malformed_or_unknown_model_output_stays_partial_and_safe():
    provider = StubProvider(
        'prefix {"status":"PARTIAL","answer":"The answer contains { braces }.",'
        '"citations":[],"missing_information":["deployment"]} trailing'
    )
    result, _ = _answer(provider)

    assert result.status == "PARTIAL"
    assert result.answer == "The answer contains { braces }."
    assert result.citations == []
    assert result.invalid_citations == []
    assert result.missing_information == ["deployment"]

    provider = StubProvider(
        {
            "status": "SUCCEEDED",
            "answer": "The contract is supported.",
            "citations": ["chunk-1"],
            "missing_information": [],
        }
    )
    result, _ = _answer(provider)

    assert result.status == "PARTIAL"
    assert result.citations == ["chunk-1"]
    assert "invalid terminal status" in result.missing_information
