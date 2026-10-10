import asyncio
import json

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
