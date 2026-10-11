from __future__ import annotations

import math
import uuid
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

    def search(
        self,
        vector: Iterable[float],
        limit: int = 10,
        *,
        owner_user_id: str | None = None,
        source_ids: Iterable[str] | None = None,
    ) -> list[VectorMatch]: ...

    def delete(self, ids: Iterable[str]) -> None: ...


class InMemoryVectorStore:
    """Deterministic test adapter with the same owner-filter contract."""

    def __init__(self, vector_size: int | None = None) -> None:
        self.vector_size = vector_size
        self._records: dict[str, VectorRecord] = {}

    def upsert(self, records: Iterable[VectorRecord]) -> None:
        for record in records:
            values = tuple(float(value) for value in record.vector)
            self._validate(record.id, values)
            self._records[record.id] = VectorRecord(
                id=record.id, vector=values, payload=dict(record.payload)
            )

    def search(
        self,
        vector: Iterable[float],
        limit: int = 10,
        *,
        owner_user_id: str | None = None,
        source_ids: Iterable[str] | None = None,
    ) -> list[VectorMatch]:
        query = tuple(float(value) for value in vector)
        self._validate("query", query)
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be positive")
        selected_sources = None if source_ids is None else set(source_ids)
        records = [
            record
            for record in self._records.values()
            if (owner_user_id is None or record.payload.get("owner_user_id") == owner_user_id)
            and (
                selected_sources is None
                or record.payload.get("source_id") in selected_sources
            )
        ]
        scored = [
            VectorMatch(
                record.id,
                self._cosine(query, record.vector),
                dict(record.payload),
            )
            for record in records
        ]
        return sorted(scored, key=lambda match: (-match.score, match.id))[:limit]

    def delete(self, ids: Iterable[str]) -> None:
        for record_id in ids:
            self._records.pop(record_id, None)

    def count(self) -> int:
        return len(self._records)

    def _validate(self, record_id: str, values: tuple[float, ...]) -> None:
        if not record_id:
            raise ValueError("vector record id must be non-empty")
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
        if left_norm == 0.0 or right_norm == 0.0:
            return 0.0
        return sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)


class VectorBackendUnavailable(RuntimeError):
    """Raised when the explicitly selected Qdrant backend is unavailable."""


class QdrantVectorStore:
    """Lazy Qdrant adapter; owner filtering is part of each candidate request."""

    def __init__(
        self,
        path: str = "storage/qdrant",
        collection: str = "domain",
        vector_size: int = 768,
        *,
        client: Any | None = None,
        models: Any | None = None,
    ) -> None:
        if not isinstance(collection, str) or not collection.strip():
            raise ValueError("collection must be non-empty")
        if isinstance(vector_size, bool) or not isinstance(vector_size, int):
            raise TypeError("vector_size must be an integer")
        if vector_size < 1:
            raise ValueError("vector_size must be positive")
        self.collection = collection
        self.vector_size = vector_size
        self.path = path
        self._models = models
        if client is None:
            try:
                from qdrant_client import QdrantClient  # type: ignore
            except ImportError as exc:
                raise VectorBackendUnavailable(
                    "Qdrant backend requested but qdrant-client is not installed"
                ) from exc
            self.client = QdrantClient(path=path)
        else:
            self.client = client
        self._ensure_collection()

    def _qdrant_models(self) -> Any:
        if self._models is not None:
            return self._models
        try:
            from qdrant_client import models  # type: ignore
        except ImportError as exc:
            raise VectorBackendUnavailable(
                "Qdrant models are unavailable; install qdrant-client"
            ) from exc
        self._models = models
        return models

    def _ensure_collection(self) -> None:
        models = self._qdrant_models()
        self.client.get_or_create_collection(
            collection_name=self.collection,
            vectors_config=models.VectorParams(
                size=self.vector_size, distance=models.Distance.COSINE
            ),
        )

    def upsert(self, records: Iterable[VectorRecord]) -> None:
        models = self._qdrant_models()
        points = []
        for record in records:
            values = tuple(float(value) for value in record.vector)
            self._validate_vector(values)
            payload = dict(record.payload)
            payload.setdefault("chunk_id", record.id)
            points.append(
                models.PointStruct(
                    id=self.point_id(record.id),
                    vector=list(values),
                    payload=payload,
                )
            )
        if points:
            self.client.upsert(collection_name=self.collection, points=points, wait=True)

    def search(
        self,
        vector: Iterable[float],
        limit: int = 10,
        *,
        owner_user_id: str | None = None,
        source_ids: Iterable[str] | None = None,
    ) -> list[VectorMatch]:
        query = tuple(float(value) for value in vector)
        self._validate_vector(query)
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be positive")
        query_filter = self._owner_filter(owner_user_id, source_ids)
        kwargs = {
            "collection_name": self.collection,
            "limit": limit,
            "query_filter": query_filter,
            "with_payload": True,
        }
        if hasattr(self.client, "query_points"):
            result = self.client.query_points(query=list(query), **kwargs)
            points = getattr(result, "points", result)
        else:
            result = self.client.search(query_vector=list(query), **kwargs)
            points = getattr(result, "points", result)
        return [self._match_from_point(point) for point in points]

    def delete(self, ids: Iterable[str]) -> None:
        identifiers = list(ids)
        if not identifiers:
            return
        models = self._qdrant_models()
        self.client.delete(
            collection_name=self.collection,
            points_selector=models.PointIdsList(
                points=[self.point_id(identifier) for identifier in identifiers]
            ),
            wait=True,
        )

    def count(self) -> int:
        result = self.client.count(collection_name=self.collection, exact=True)
        return int(result.count)

    def _owner_filter(
        self,
        owner_user_id: str | None,
        source_ids: Iterable[str] | None,
    ) -> Any:
        """Build a server-side owner/source predicate for candidate requests."""

        models = self._qdrant_models()
        must: list[Any] = []
        if owner_user_id is not None:
            if not isinstance(owner_user_id, str) or not owner_user_id.strip():
                raise ValueError("owner_user_id must be non-empty")
            must.append(
                models.FieldCondition(
                    key="owner_user_id",
                    match=models.MatchValue(value=owner_user_id),
                )
            )
        if source_ids is not None:
            selected = sorted({str(source_id) for source_id in source_ids if str(source_id)})
            if selected:
                if not hasattr(models, "MatchAny"):
                    raise VectorBackendUnavailable(
                        "Qdrant client does not support source selection filters"
                    )
                must.append(
                    models.FieldCondition(
                        key="source_id",
                        match=models.MatchAny(any=selected),
                    )
                )
        return models.Filter(must=must) if must else None

    def _validate_vector(self, values: tuple[float, ...]) -> None:
        if len(values) != self.vector_size:
            raise ValueError(
                f"vector has dimension {len(values)}; expected {self.vector_size}"
            )
        if not values or not all(math.isfinite(value) for value in values):
            raise ValueError("vector values must be finite")

    @staticmethod
    def point_id(canonical_id: str) -> str:
        if not isinstance(canonical_id, str) or not canonical_id.strip():
            raise ValueError("canonical vector record id must be non-empty")
        return str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"local-multi-agent-rag:knowledge:{canonical_id}",
            )
        )

    @staticmethod
    def _match_from_point(point: Any) -> VectorMatch:
        payload = dict(getattr(point, "payload", None) or {})
        canonical_id = payload.get("chunk_id")
        if not isinstance(canonical_id, str) or not canonical_id.strip():
            canonical_id = str(point.id)
        return VectorMatch(
            id=canonical_id,
            score=float(point.score),
            payload=payload,
        )


QdrantStore = QdrantVectorStore


__all__ = [
    "InMemoryVectorStore",
    "QdrantStore",
    "QdrantVectorStore",
    "VectorBackendUnavailable",
    "VectorMatch",
    "VectorRecord",
    "VectorStore",
]
