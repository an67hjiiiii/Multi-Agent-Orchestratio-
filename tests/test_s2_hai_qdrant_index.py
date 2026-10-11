from __future__ import annotations

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
from app.storage.postgres.base import Base
from app.storage.postgres.runtime import PostgresAuthStore, PostgresSourceStore
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
