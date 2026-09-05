from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Iterable, Protocol


@dataclass(frozen=True)
class VectorRecord:
    id: str
    vector: tuple[float, ...]
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VectorMatch:
    id: str
    score: float
    payload: dict[str, Any] = field(default_factory=dict)


class VectorStore(Protocol):
    def upsert(self, records: Iterable[VectorRecord]) -> None: ...

    def search(self, vector: Iterable[float], limit: int = 10) -> list[VectorMatch]: ...

    def delete(self, ids: Iterable[str]) -> None: ...


class InMemoryVectorStore:
    """Deterministic local fake for unit tests and storage-boundary checks."""

    def __init__(self, vector_size: int | None = None) -> None:
        self.vector_size = vector_size
        self._records: dict[str, VectorRecord] = {}

    def upsert(self, records: Iterable[VectorRecord]) -> None:
        for record in records:
            self._validate(record.id, record.vector)
            self._records[record.id] = VectorRecord(
                id=record.id,
                vector=tuple(record.vector),
                payload=dict(record.payload),
            )

    def search(self, vector: Iterable[float], limit: int = 10) -> list[VectorMatch]:
        query = tuple(float(value) for value in vector)
        self._validate("query", query)
        if limit < 1:
            raise ValueError("limit must be positive")
        scored = [
            VectorMatch(record.id, self._cosine(query, record.vector), dict(record.payload))
            for record in self._records.values()
        ]
        return sorted(scored, key=lambda match: (-match.score, match.id))[:limit]

    def delete(self, ids: Iterable[str]) -> None:
        for record_id in ids:
            self._records.pop(record_id, None)

    def count(self) -> int:
        return len(self._records)

    def _validate(self, record_id: str, vector: Iterable[float]) -> None:
        if not record_id:
            raise ValueError("vector record id must be non-empty")
        values = tuple(float(value) for value in vector)
        if not values:
            raise ValueError("vector must not be empty")
        if not all(math.isfinite(value) for value in values):
            raise ValueError("vector values must be finite")
        if self.vector_size is not None and len(values) != self.vector_size:
            raise ValueError(
                f"vector has dimension {len(values)}; expected {self.vector_size}"
            )

    @staticmethod
    def _cosine(left: tuple[float, ...], right: tuple[float, ...]) -> float:
        if len(left) != len(right):
            raise ValueError("query and stored vectors must have the same dimension")
        left_norm = math.sqrt(sum(value * value for value in left))
        right_norm = math.sqrt(sum(value * value for value in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)


class VectorBackendUnavailable(RuntimeError):
    """Raised when the optional Qdrant backend is requested but unavailable."""


class QdrantVectorStore:
    """Thin, lazy Qdrant boundary; importing this module stays dependency-free."""

    def __init__(
        self,
        path: str = "storage/qdrant",
        collection: str = "domain",
        vector_size: int = 768,
        *,
        client: Any | None = None,
    ) -> None:
        if not collection.strip():
            raise ValueError("collection must be non-empty")
        if vector_size < 1:
            raise ValueError("vector_size must be positive")
        self.collection = collection
        self.vector_size = vector_size
        if client is None:
            try:
                from qdrant_client import QdrantClient  # type: ignore
            except ImportError as exc:
                raise VectorBackendUnavailable(
                    "Qdrant backend requested but qdrant-client is not installed; "
                    "install the optional dependency before enabling it"
                ) from exc
            self.client = QdrantClient(path=path)
        else:
            self.client = client
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        try:
            from qdrant_client import models  # type: ignore
        except ImportError as exc:
            raise VectorBackendUnavailable(
                "Qdrant models are unavailable; install qdrant-client"
            ) from exc
        self.client.get_or_create_collection(
            collection_name=self.collection,
            vectors_config=models.VectorParams(
                size=self.vector_size, distance=models.Distance.COSINE
            ),
        )

    def upsert(self, records: Iterable[VectorRecord]) -> None:
        try:
            from qdrant_client import models  # type: ignore
        except ImportError as exc:
            raise VectorBackendUnavailable("Qdrant models are unavailable") from exc
        points = []
        for record in records:
            values = tuple(float(value) for value in record.vector)
            if len(values) != self.vector_size:
                raise ValueError(
                    f"vector has dimension {len(values)}; expected {self.vector_size}"
                )
            points.append(
                models.PointStruct(
                    id=record.id, vector=list(values), payload=dict(record.payload)
                )
            )
        if points:
            self.client.upsert(collection_name=self.collection, points=points, wait=True)

    def search(self, vector: Iterable[float], limit: int = 10) -> list[VectorMatch]:
        query = [float(value) for value in vector]
        if len(query) != self.vector_size:
            raise ValueError(
                f"vector has dimension {len(query)}; expected {self.vector_size}"
            )
        if limit < 1:
            raise ValueError("limit must be positive")
        if hasattr(self.client, "query_points"):
            result = self.client.query_points(
                collection_name=self.collection, query=query, limit=limit
            )
            points = getattr(result, "points", result)
        else:
            points = self.client.search(
                collection_name=self.collection, query_vector=query, limit=limit
            )
        return [
            VectorMatch(
                id=str(point.id), score=float(point.score), payload=dict(point.payload or {})
            )
            for point in points
        ]

    def delete(self, ids: Iterable[str]) -> None:
        identifiers = list(ids)
        if not identifiers:
            return
        try:
            from qdrant_client import models  # type: ignore
        except ImportError as exc:
            raise VectorBackendUnavailable("Qdrant models are unavailable") from exc
        self.client.delete(
            collection_name=self.collection,
            points_selector=models.PointIdsList(points=identifiers),
            wait=True,
        )

    def count(self) -> int:
        result = self.client.count(collection_name=self.collection, exact=True)
        return int(result.count)


QdrantStore = QdrantVectorStore
