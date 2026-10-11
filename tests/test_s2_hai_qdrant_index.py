from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from app.retrieval.candidate_index import CandidateIndex, IndexingError
from app.retrieval.embeddings import LocalHashEmbedder
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
