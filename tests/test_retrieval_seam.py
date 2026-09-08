from __future__ import annotations

import asyncio
from pathlib import Path

from app.research.pipeline import ResearchPipeline
from app.storage.run_store import RunStore
from app.storage.source_store import SourceStore


class AsyncRetriever:
    def __init__(self, source_store: SourceStore):
        self.chunk = source_store.chunks()[0]
        self.calls: list[str] = []

    def index_identity(self) -> dict[str, object]:
        return {
            "retrieval_backend": "ollama-qdrant",
            "index_version": "domain-v2",
            "embedding_version": "nomic-embed-v1",
            "embedding_model": "nomic-embed-text",
            "embedding_digest": "sha256:embed-v1",
            "embedding_dimension": 768,
            "corpus_snapshot_id": "corpus_0123456789abcdef",
            "collection": "domain",
            "readiness": "READY",
            "private_value": "must-not-enter-trace",
        }

    async def asearch(self, query: str, **_kwargs):
        return await self.search(query)

    async def search(self, query: str, **_kwargs):
        self.calls.append(query)
        return [self.chunk]


def _pipeline(tmp_path: Path, monkeypatch, retriever):
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "dev")
    monkeypatch.setenv("PROVIDER", "fake")
    sources = SourceStore(tmp_path / "data")
    sources.import_text("api.md", "The API contract defines request validation.")
    if retriever == "build":
        retriever = AsyncRetriever(sources)
    return ResearchPipeline(
        sources,
        RunStore(tmp_path / "runs"),
        retriever=retriever,
    ), retriever


def test_async_retriever_is_shared_by_vanilla_and_task_paths(tmp_path, monkeypatch):
    pipeline, retriever = _pipeline(tmp_path, monkeypatch, "build")

    vanilla = asyncio.run(pipeline.run("request validation", "A", "fake"))
    planned = asyncio.run(pipeline.run("Review API", "B", "fake"))

    assert vanilla["status"] == "COMPLETE"
    assert planned["status"] != "FAILED"
    assert len(retriever.calls) >= 2
    assert vanilla["retrieval"] == {
        "retrieval_backend": "ollama-qdrant",
        "index_version": "domain-v2",
        "embedding_version": "nomic-embed-v1",
        "embedding_model": "nomic-embed-text",
        "embedding_digest": "sha256:embed-v1",
        "embedding_dimension": 768,
        "corpus_snapshot_id": "corpus_0123456789abcdef",
        "collection": "domain",
        "readiness": "READY",
        "retrieval_scoring_version": "lexical-overlap-v1",
        "domain_ranking_version": "canonical-registry-domain-v1",
    }
    assert vanilla["effective_config"]["retrieval"] == vanilla["retrieval"]
    assert all(
        event["retrieval"]["index_version"] == "domain-v2"
        for event in vanilla["events"]
        if "retrieval" in event
    )


def test_retriever_contract_failure_is_terminal_and_does_not_fallback(
    tmp_path, monkeypatch
):
    class BrokenRetriever:
        def __init__(self):
            self.calls = 0

        async def search(self, query: str, **_kwargs):
            self.calls += 1
            return ["not-a-source-chunk"]

    retriever = BrokenRetriever()
    pipeline, _ = _pipeline(tmp_path, monkeypatch, retriever)

    run = asyncio.run(pipeline.run("request validation", "A", "fake"))

    assert run["status"] == "FAILED"
    assert retriever.calls == 1
    assert any(
        event["stage"] == "run_failed" and event["error_type"] == "TypeError"
        for event in run["events"]
    )


def test_injected_retriever_without_identity_is_explicitly_custom_unknown(
    tmp_path, monkeypatch
):
    class UnidentifiedRetriever:
        async def search(self, query: str, **_kwargs):
            return [SourceStore(tmp_path / "data").chunks()[0]]

    pipeline, _ = _pipeline(tmp_path, monkeypatch, "build")
    pipeline.retrieval_owner = UnidentifiedRetriever()
    pipeline.retriever = pipeline.retrieval_owner

    run = asyncio.run(pipeline.run("request validation", "A", "fake"))

    assert run["status"] == "COMPLETE"
    assert run["retrieval"]["retrieval_backend"] == "custom"
    assert run["retrieval"]["readiness"] == "unknown"
    assert run["retrieval"]["embedding_model"] is None
