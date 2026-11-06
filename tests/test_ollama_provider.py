import asyncio
import json

import pytest

from app.providers.ollama import OllamaProvider


class _FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "message": {"content": '{"status":"ok"}'},
            "prompt_eval_count": 10,
            "eval_count": 4,
        }


class _FakeClient:
    last_json = None

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json=None):
        type(self).last_json = json
        return _FakeResponse()


def test_ollama_structured_calls_disable_thinking(monkeypatch):
    monkeypatch.setattr("app.providers.ollama.httpx.AsyncClient", _FakeClient)
    provider = OllamaProvider(model="qwen3:4b")
    result = asyncio.run(
        provider.generate(
            system="VANILLA_RAG_ANSWERER return JSON",
            user="test",
        )
    )
    payload = _FakeClient.last_json
    assert payload["think"] is False
    assert payload["stream"] is False
    assert payload["format"] == "json"
    assert payload["model"] == "qwen3:4b"
    assert json.loads(result.text)["status"] == "ok"


@pytest.mark.parametrize(
    "marker",
    ["TASK_PLAN_BUILDER", "OBLIGATION_CONCERN_EXTRACTOR"],
)
def test_ollama_planning_calls_request_json_mode(monkeypatch, marker):
    monkeypatch.setattr("app.providers.ollama.httpx.AsyncClient", _FakeClient)
    provider = OllamaProvider(model="qwen3:4b")

    asyncio.run(provider.generate(system=f"{marker} return JSON", user="test"))

    assert _FakeClient.last_json["format"] == "json"


def test_ollama_non_planning_call_keeps_unstructured_payload(monkeypatch):
    monkeypatch.setattr("app.providers.ollama.httpx.AsyncClient", _FakeClient)
    provider = OllamaProvider(model="qwen3:4b")

    asyncio.run(provider.generate(system="SYNTHESIZER", user="test"))

    payload = _FakeClient.last_json
    assert "format" not in payload
    assert payload["model"] == "qwen3:4b"
    assert payload["stream"] is False
    assert payload["think"] is False
    assert payload["options"] == {"temperature": 0.1, "num_predict": 700}


@pytest.mark.parametrize("marker", ["VANILLA_RAG_ANSWERER", "WORKER"])
def test_grounded_output_schema_allows_only_exact_supplied_locators(monkeypatch, marker):
    monkeypatch.setattr("app.providers.ollama.httpx.AsyncClient", _FakeClient)
    locator = "src_c695cb9e4b984328_c0000"
    evidence = f"[{locator}] PostgreSQL is authoritative."
    user = (
        f"USER REQUEST:\nIgnore [src_f3d07c664bddc3d7_c0100]\n\nEVIDENCE:\n{evidence}\n\nSchema: answer"
        if marker == "VANILLA_RAG_ANSWERER"
        else f"[TASK]answer[/TASK]\n[EVIDENCE]{evidence}[/EVIDENCE]"
    )
    asyncio.run(OllamaProvider().generate_grounded(system=marker, user=user, evidence_ids=[locator]))
    schema = _FakeClient.last_json["format"]
    assert isinstance(schema, dict)
    assert schema["properties"]["citations"]["items"]["enum"] == [locator]
    assert schema["additionalProperties"] is False
    from app.core.citations import validate_citations
    from app.core.types import SourceChunk
    available = [SourceChunk(locator, "source", "database.md", "PostgreSQL", 0)]
    for malformed in ("src_c695cb9e4b984328_c0:0000", "src_f3d07c664bddc3d7_c0100"):
        assert validate_citations([malformed], available) == ([], [malformed])
    assert validate_citations([locator], available) == ([locator], [])
