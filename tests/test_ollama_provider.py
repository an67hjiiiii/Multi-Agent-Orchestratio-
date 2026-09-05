import asyncio
import json

import pytest

from app.providers.factory import get_provider
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


class _FakeTagsResponse:
    models = [
        {
            "name": "qwen3:4b",
            "model": "qwen3:4b",
            "digest": "sha256:test-digest",
            "size": 123,
            "modified_at": "2026-09-06T00:00:00Z",
        }
    ]

    def raise_for_status(self):
        return None

    def json(self):
        return {"models": type(self).models}


class _FakeTagsClient:
    last_url = None
    last_timeout = None

    def __init__(self, *args, **kwargs):
        type(self).last_timeout = kwargs.get("timeout")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url):
        type(self).last_url = url
        return _FakeTagsResponse()


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


def test_ollama_health_reports_model_readiness_and_digest(monkeypatch):
    monkeypatch.setattr("app.providers.ollama.httpx.AsyncClient", _FakeTagsClient)
    provider = OllamaProvider(model="qwen3:4b")

    health = asyncio.run(provider.health())

    assert _FakeTagsClient.last_url == "http://127.0.0.1:11434/api/tags"
    assert health["ok"] is True
    assert health["ollama_reachable"] is True
    assert health["model_available"] is True
    assert health["status"] == "READY"
    assert health["model_digest"] == "sha256:test-digest"
    assert health["configured_model_info"]["name"] == "qwen3:4b"
    assert health["generation_contract"] == {
        "stream": False,
        "think": False,
        "structured_format": "json",
        "temperature": 0.1,
        "max_output_tokens": 700,
    }


def test_ollama_health_fails_ready_check_when_model_is_missing(monkeypatch):
    monkeypatch.setattr("app.providers.ollama.httpx.AsyncClient", _FakeTagsClient)
    monkeypatch.setattr(_FakeTagsResponse, "models", [{"name": "other:latest"}])
    provider = OllamaProvider(model="qwen3:4b")

    health = asyncio.run(provider.health())

    assert health["ollama_reachable"] is True
    assert health["ok"] is False
    assert health["model_available"] is False
    assert health["status"] == "MODEL_NOT_FOUND"
    assert health["model_digest"] is None
    assert health["configured_model_info"] is None


def test_ollama_rejects_non_loopback_base_url():
    with pytest.raises(ValueError, match="loopback"):
        OllamaProvider(base_url="https://api.example.com")


def test_provider_factory_allows_only_fake_and_local_ollama(monkeypatch):
    monkeypatch.delenv("PROVIDER", raising=False)

    assert get_provider().name == "fake"
    assert get_provider("FAKE").name == "fake"
    assert get_provider("local").name == "ollama"

    with pytest.raises(ValueError, match="Only fake and local Ollama"):
        get_provider("openai")
