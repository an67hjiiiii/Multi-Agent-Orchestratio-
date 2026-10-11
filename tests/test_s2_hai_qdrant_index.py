from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main as main_module
from app.auth.store import AuthStore
from app.main import app
from app.retrieval.candidate_index import CandidateIndex, IndexingError
from app.retrieval.embeddings import LocalHashEmbedder
from app.research.pipeline import ResearchPipeline
from app.storage.postgres.base import Base
from app.storage.postgres.runtime import PostgresAuthStore, PostgresSourceStore
from app.storage.run_store import RunStore
from app.storage.source_store import SourceStore
from app.storage.vector_store import (
    InMemoryVectorStore,
    QdrantVectorStore,
    VectorRecord,
)


def test_in_memory_candidate_search_filters_owner_and_source():
    embedder = LocalHashEmbedder(dimension=8)
    index = InMemoryVectorStore(vector_size=8)
    index.upsert(
        [
            VectorRecord(
                "chunk-a",
                embedder.embed("alpha evidence"),
                {"owner_user_id": "owner-a", "source_id": "source-a"},
            ),
            VectorRecord(
                "chunk-b",
                embedder.embed("alpha evidence"),
                {"owner_user_id": "owner-b", "source_id": "source-b"},
            ),
        ]
    )

    matches = index.search(
        embedder.embed("alpha"),
        owner_user_id="owner-a",
        source_ids=["source-a"],
    )
    assert [match.id for match in matches] == ["chunk-a"]


def test_pipeline_uses_owner_scoped_vector_candidates_when_enabled(tmp_path):
    embedder = LocalHashEmbedder(dimension=8)
    vector_store = InMemoryVectorStore(vector_size=8)
    owner_a_store = SourceStore(str(tmp_path / "owner-a"))
    owner_b_store = SourceStore(str(tmp_path / "owner-b"))
    owner_a = owner_a_store.import_text("a.md", "alpha owner a evidence")
    owner_b = owner_b_store.import_text("b.md", "alpha owner b evidence")
    CandidateIndex(
        owner_a_store, vector_store, owner_user_id="owner-a", embedder=embedder
    ).index_source(owner_a["source_id"])
    CandidateIndex(
        owner_b_store, vector_store, owner_user_id="owner-b", embedder=embedder
    ).index_source(owner_b["source_id"])
    pipeline = ResearchPipeline(
        owner_a_store,
        RunStore(str(tmp_path / "runs")),
        candidate_index=CandidateIndex(
            owner_a_store, vector_store, owner_user_id="owner-a", embedder=embedder
        ),
        retrieval_backend="memory",
    )

    candidates = pipeline._retrieve_candidates(
        "alpha evidence",
        owner_a_store.chunks(),
        top_k=1,
        min_score=0.0,
        source_ids=[owner_a["source_id"]],
    )

    assert len(candidates) == 1
    assert candidates[0].source_id == owner_a["source_id"]
    assert candidates[0].score > 0


def test_chat_uses_real_qdrant_candidates_when_explicitly_enabled(tmp_path, monkeypatch):
    pytest.importorskip("qdrant_client")
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "m0")
    monkeypatch.setattr(main_module, "STORAGE_BACKEND", "file")
    monkeypatch.setattr(main_module, "DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr(main_module, "RUNS_DIR", str(tmp_path / "runs"))
    monkeypatch.setattr(main_module, "VECTOR_BACKEND", "qdrant")
    monkeypatch.setattr(main_module, "VECTOR_INDEX_PATH", str(tmp_path / "qdrant"))
    monkeypatch.setattr(main_module, "VECTOR_COLLECTION", "s2-chat-test")
    monkeypatch.setattr(main_module, "VECTOR_SIZE", "8")
    monkeypatch.setattr(main_module, "_derived_vector_store", None)
    monkeypatch.setattr(main_module, "_derived_vector_store_backend", None)
    auth = AuthStore(tmp_path / "auth")
    user = auth.register(email="qdrant-chat@example.test", password="long-enough-password")
    token, _ = auth.create_session(user["user_id"])
    app.state.auth_store = auth
    headers = {"Authorization": f"Bearer {token}"}

    try:
        with TestClient(app) as client:
            uploaded = client.post(
                "/api/sources/text",
                headers=headers,
                json={"source_name": "alpha.md", "text": "Alpha evidence is stored in this private source."},
            )
            run = client.post(
                "/api/chat",
                headers=headers,
                json={"message": "What alpha evidence is available?", "condition": "A", "provider": "fake"},
            )
        assert uploaded.status_code == 200
        assert run.status_code == 200
        assert run.json()["status"] == "COMPLETE"
        retrieval = next(event for event in run.json()["events"] if event["stage"] == "vanilla_retrieval")
        assert retrieval["retrieval_backend"] == "qdrant"
        assert retrieval["selected"]
        assert run.json()["task_results"][0]["citations"] == retrieval["selected"]
    finally:
        vector_store = main_module._derived_vector_store
        if vector_store is not None and hasattr(vector_store.client, "close"):
            vector_store.client.close()
        monkeypatch.setattr(main_module, "_derived_vector_store", None)
        monkeypatch.setattr(main_module, "_derived_vector_store_backend", None)


def test_pipeline_does_not_fall_back_when_enabled_vector_search_fails(tmp_path, monkeypatch):
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "m0")
    source_store = SourceStore(str(tmp_path / "data"))
    source_store.import_text("source.md", "alpha evidence is available")

    class UnavailableCandidates:
        def candidates(self, query, *, limit, source_ids=None):
            raise RuntimeError("vector backend unavailable")

    pipeline = ResearchPipeline(
        source_store,
        RunStore(str(tmp_path / "runs")),
        candidate_index=UnavailableCandidates(),
        retrieval_backend="qdrant",
    )
    run = asyncio.run(pipeline.run("alpha evidence", "A", "fake"))

    assert run["status"] == "FAILED"
    assert any(event["stage"] == "run_failed" for event in run["events"])
    retrieval = run["effective_config"]["retrieval_backend"]
    assert retrieval == "qdrant"


class _FakeModels:
    class Distance:
        COSINE = "Cosine"

    @dataclass
    class VectorParams:
        size: int
        distance: str

    @dataclass
    class MatchValue:
        value: str

    @dataclass
    class MatchAny:
        any: list[str]

    @dataclass
    class FieldCondition:
        key: str
        match: object

    @dataclass
    class Filter:
        must: list[object]

    @dataclass
    class PointStruct:
        id: str
        vector: list[float]
        payload: dict

    @dataclass
    class PointIdsList:
        points: list[str]


@dataclass
class _Point:
    id: str
    score: float
    payload: dict


class _FakeQdrant:
    def __init__(self):
        self.search_kwargs = None

    def get_or_create_collection(self, **kwargs):
        self.collection_kwargs = kwargs

    def query_points(self, **kwargs):
        self.search_kwargs = kwargs
        return type("QueryResult", (), {"points": []})()


def test_qdrant_candidate_request_contains_owner_filter():
    client = _FakeQdrant()
    store = QdrantVectorStore(
        collection="test",
        vector_size=2,
        client=client,
        models=_FakeModels,
    )
    store.search(
        [1.0, 0.0],
        owner_user_id="owner-a",
        source_ids=["source-a", "source-b"],
    )
    query_filter = client.search_kwargs["query_filter"]
    assert {(item.key, type(item.match).__name__, getattr(item.match, "value", None)) for item in query_filter.must if item.key == "owner_user_id"} == {
        ("owner_user_id", "MatchValue", "owner-a")
    }
    source_condition = next(item for item in query_filter.must if item.key == "source_id")
    assert source_condition.match.any == ["source-a", "source-b"]


def test_real_qdrant_local_upsert_and_owner_source_filtered_top_k(tmp_path):
    qdrant_client = pytest.importorskip("qdrant_client")
    from qdrant_client import QdrantClient

    client = QdrantClient(path=str(tmp_path / "qdrant"))
    try:
        store = QdrantVectorStore(
            path=str(tmp_path / "qdrant"),
            collection="local-filter-test",
            vector_size=4,
            client=client,
        )
        store.upsert(
            [
                VectorRecord(
                    "owner-a:chunk-a",
                    (1.0, 0.0, 0.0, 0.0),
                    {"owner_user_id": "owner-a", "source_id": "source-a", "chunk_id": "chunk-a"},
                ),
                VectorRecord(
                    "owner-a:chunk-b",
                    (0.9, 0.1, 0.0, 0.0),
                    {"owner_user_id": "owner-a", "source_id": "source-b", "chunk_id": "chunk-b"},
                ),
                VectorRecord(
                    "owner-b:chunk-c",
                    (1.0, 0.0, 0.0, 0.0),
                    {"owner_user_id": "owner-b", "source_id": "source-a", "chunk_id": "chunk-c"},
                ),
            ]
        )
        matches = store.search(
            (1.0, 0.0, 0.0, 0.0),
            limit=1,
            owner_user_id="owner-a",
            source_ids=["source-a"],
        )
        assert [match.id for match in matches] == ["chunk-a"]
    finally:
        client.close()


def test_candidate_index_marks_authoritative_source_failed_on_index_error(tmp_path: Path):
    class FailingIndex:
        def upsert(self, records):
            raise RuntimeError("qdrant unavailable")

    store = SourceStore(str(tmp_path / "data"))
    imported = store.import_text("guide.md", "authoritative text")
    index = CandidateIndex(
        store,
        FailingIndex(),
        owner_user_id="owner-a",
        embedder=LocalHashEmbedder(dimension=8),
    )
    with pytest.raises(IndexingError):
        index.index_source(imported["source_id"])


def test_postgres_authoritative_source_fails_closed_when_derived_index_fails():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    event.listen(
        engine,
        "connect",
        lambda connection, _record: connection.create_function(
            "btrim", 1, lambda value: value.strip()
        ),
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    owner = PostgresAuthStore(factory).register(
        email="index-failure@example.test", password="long-enough-password"
    )
    source_store = PostgresSourceStore(factory, owner["user_id"])
    imported = source_store.import_text("guide.md", "Authoritative source text.")

    class FailingIndex:
        def upsert(self, records):
            raise RuntimeError("derived backend unavailable")

    index = CandidateIndex(
        source_store,
        FailingIndex(),
        owner_user_id=owner["user_id"],
    )
    with pytest.raises(IndexingError):
        index.index_source(imported["source_id"])
    assert source_store.source_status(imported["source_id"])["status"] == "FAILED"
    assert source_store.chunks() == []


def test_api_ingestion_invokes_explicit_memory_index_for_text_and_file(tmp_path, monkeypatch):
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "m0")
    monkeypatch.setattr(main_module, "DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr(main_module, "RUNS_DIR", str(tmp_path / "runs"))
    monkeypatch.setattr(main_module, "STORAGE_BACKEND", "file")
    monkeypatch.setattr(main_module, "VECTOR_BACKEND", "memory")
    monkeypatch.setattr(main_module, "VECTOR_SIZE", "8")
    monkeypatch.setattr(main_module, "_derived_vector_store", None)
    monkeypatch.setattr(main_module, "_derived_vector_store_backend", None)
    auth = AuthStore(tmp_path / "auth")
    user = auth.register(email="index-api@example.test", password="long-enough-password")
    token, _ = auth.create_session(user["user_id"])
    app.state.auth_store = auth
    headers = {"Authorization": f"Bearer {token}"}

    with TestClient(app) as client:
        text_response = client.post(
            "/api/sources/text",
            headers=headers,
            json={"source_name": "text.md", "text": "Text ingestion evidence."},
        )
        file_response = client.post(
            "/api/sources/file",
            headers=headers,
            files={"file": ("file.txt", b"File ingestion evidence.", "text/plain")},
        )

    assert text_response.status_code == 200
    assert file_response.status_code == 200
    assert text_response.json()["derived_index"]["backend"] == "memory"
    assert file_response.json()["derived_index"]["chunks_indexed"] == 1
    assert main_module._derived_vector_store.count() == 2


def test_api_index_failure_returns_503_and_marks_file_source_failed(tmp_path, monkeypatch):
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "m0")
    monkeypatch.setattr(main_module, "DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr(main_module, "STORAGE_BACKEND", "file")
    monkeypatch.setattr(main_module, "VECTOR_BACKEND", "memory")

    class FailingIndex:
        def upsert(self, records):
            raise RuntimeError("memory index unavailable")

    monkeypatch.setattr(main_module, "_derived_vector_store", FailingIndex())
    monkeypatch.setattr(main_module, "_derived_vector_store_backend", "memory")
    auth = AuthStore(tmp_path / "auth")
    user = auth.register(email="index-api-failure@example.test", password="long-enough-password")
    token, _ = auth.create_session(user["user_id"])
    app.state.auth_store = auth
    headers = {"Authorization": f"Bearer {token}"}

    with TestClient(app) as client:
        response = client.post(
            "/api/sources/text",
            headers=headers,
            json={"source_name": "failed.md", "text": "This must not become ready."},
        )
        source_id = next(
            item["source_id"]
            for item in client.get("/api/sources", headers=headers).json()["sources"]
        )
        source = client.get(f"/api/sources/{source_id}", headers=headers)

    assert response.status_code == 503
    assert source.json()["status"] == "FAILED"
