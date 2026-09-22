from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from app.core.storage_config import StorageConfig
from app.core.types import SourceChunk
from app.retrieval.embeddings import (
    EmbeddingBackendUnavailable,
    LocalHashEmbedder,
    OllamaEmbedder,
    TextEmbedder,
)
from app.retrieval.query import retrieve_chunks
from app.storage.source_store import SourceStore
from app.storage.vector_store import (
    InMemoryVectorStore,
    QdrantVectorStore,
    VectorBackendUnavailable,
    VectorStore,
)


class KnowledgeBase:
    """Small local document/index facade over the canonical SourceStore."""

    def __init__(
        self,
        source_store: SourceStore,
        *,
        vector_store: VectorStore | None = None,
        embedder: TextEmbedder | None = None,
        backend_name: str | None = None,
        retrieval_mode: str | None = None,
        availability_error: str | None = None,
    ) -> None:
        self.source_store = source_store
        self.vector_store = vector_store
        self.embedder = embedder or LocalHashEmbedder()
        self.retrieval_mode = (
            retrieval_mode or ("VECTOR" if vector_store is not None else "LEXICAL")
        ).strip().upper()
        if self.retrieval_mode not in {"LEXICAL", "VECTOR", "HYBRID"}:
            raise ValueError(f"Unsupported retrieval mode {self.retrieval_mode}")
        self.availability_error = availability_error
        vector_dimension = getattr(vector_store, "vector_size", None)
        if vector_dimension is not None and vector_dimension != self.embedder.dimension:
            raise ValueError(
                f"embedding dimension {self.embedder.dimension} does not match "
                f"vector store dimension {vector_dimension}"
            )
        self.backend_name = backend_name or (
            "lexical" if vector_store is None else type(vector_store).__name__
        )
        if vector_store is not None:
            self._sync_index()

    @classmethod
    def from_env(cls, source_store: SourceStore) -> "KnowledgeBase":
        """Build the optional vector path only when the user enables it.

        The unset state intentionally keeps the previous lexical LKG.  An
        explicitly requested but unavailable Qdrant backend raises instead of
        silently changing the configured implementation.
        """

        config = StorageConfig.from_env()
        if config.retrieval_mode == "LEXICAL":
            return cls(
                source_store,
                backend_name="lexical",
                retrieval_mode="LEXICAL",
            )

        try:
            embedder: TextEmbedder
            if config.embedding_provider == "ollama":
                embedder = OllamaEmbedder(
                    model=config.embedding_model,
                    dimension=config.vector_size,
                )
            else:
                embedder = LocalHashEmbedder(dimension=config.vector_size)
            if config.vector_backend == "memory":
                vector_store: VectorStore = InMemoryVectorStore(
                    vector_size=config.vector_size
                )
            else:
                vector_store = QdrantVectorStore(
                    path=config.qdrant_path,
                    collection=config.qdrant_collection,
                    vector_size=config.vector_size,
                )
            return cls(
                source_store,
                vector_store=vector_store,
                embedder=embedder,
                backend_name=config.vector_backend,
                retrieval_mode=config.retrieval_mode,
            )
        except (
            EmbeddingBackendUnavailable,
            ImportError,
            OSError,
            ValueError,
            VectorBackendUnavailable,
        ) as exc:
            # Keep startup deterministic and let the API report an explicit
            # unavailable vector mode instead of silently using lexical search.
            return cls(
                source_store,
                backend_name="unavailable",
                retrieval_mode=config.retrieval_mode,
                availability_error=str(exc),
            )

    def import_text(
        self,
        source_name: str,
        text: str,
        *,
        provenance: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        result = self.source_store.import_text(
            source_name,
            text,
            provenance=provenance,
        )
        indexed = self._index_source(result["source_id"])
        return {
            **result,
            "retrieval_backend": self.backend_name,
            "retrieval_mode": self.retrieval_mode,
            "backend": self.backend_name,
            "source_type": result.get("provenance", {}).get("source_type"),
            "source_format": result.get("provenance", {}).get("source_format"),
            "index_status": "READY" if self.retrieval_mode == "LEXICAL" or self.vector_store is not None else "UNAVAILABLE",
            "embedding_version": self.embedder.version
            if self.vector_store is not None
            else None,
            "vector_indexed_chunks": indexed,
        }

    @property
    def is_available(self) -> bool:
        return self.retrieval_mode == "LEXICAL" or self.vector_store is not None

    def import_document(
        self,
        source_name: str,
        data: bytes | str,
        *,
        origin: str = "upload",
        content_type: str | None = None,
    ) -> dict[str, Any]:
        from app.ingestion.documents import extract_document

        document = extract_document(
            data,
            source_name,
            origin=origin,
            content_type=content_type,
        )
        return self.import_text(
            document.source_name,
            document.text,
            provenance=document.provenance,
        )

    def import_path(self, path: str | Path) -> dict[str, Any]:
        from app.ingestion.documents import extract_document_path

        document = extract_document_path(path)
        return self.import_text(
            document.source_name,
            document.text,
            provenance=document.provenance,
        )

    def list_sources(self) -> list[dict[str, Any]]:
        sources = self.source_store.list_sources()
        for source in sources:
            source["index_status"] = (
                "UNAVAILABLE"
                if not self.is_available
                else "READY"
                if int(source.get("chunk_count", 0) or 0) > 0
                else "EMPTY"
            )
        return sources

    def source(self, source_id: str) -> dict[str, Any] | None:
        return self.source_store.source(source_id)

    def chunk(self, chunk_id: str) -> dict[str, Any] | None:
        return self.source_store.chunk(chunk_id)

    def status(self) -> dict[str, Any]:
        status = self.source_store.status()
        reported_retrieval_backend = (
            "hybrid" if self.retrieval_mode == "HYBRID" else self.backend_name
        )
        if self.retrieval_mode != "LEXICAL" and self.vector_store is None:
            status.update(
                {
                    "status": "UNAVAILABLE",
                    "backend": self.backend_name,
                    "retrieval_mode": self.retrieval_mode,
                    "retrieval_backend": reported_retrieval_backend,
                    "embedding_version": None,
                    "vector_indexed_chunks": 0,
                    "index_status": "UNAVAILABLE",
                    "availability_error": self.availability_error,
                }
            )
            return status
        status.update(
            {
                "backend": "local_json" if self.retrieval_mode == "LEXICAL" else self.backend_name,
                "retrieval_mode": self.retrieval_mode,
                "retrieval_backend": reported_retrieval_backend,
                "embedding_version": self.embedder.version
                if self.vector_store is not None
                else None,
                "vector_indexed_chunks": self._vector_count(),
                "index_status": (
                    "NOT_CONFIGURED"
                    if self.retrieval_mode == "LEXICAL"
                    else "READY"
                    if self._vector_count()
                    else "EMPTY"
                ),
            }
        )
        return status

    def search(
        self,
        query: str,
        *,
        top_k: int = 6,
        min_score: float = 0.0,
        domain: str | None = None,
        task_domain: str | None = None,
    ) -> list[SourceChunk]:
        """Search canonical chunks using the configured local retrieval mode."""

        return retrieve_chunks(
            query,
            self.source_store.chunks(),
            retrieval_mode=self.retrieval_mode,
            vector_store=self.vector_store,
            embedder=self.embedder,
            top_k=top_k,
            min_score=min_score,
            domain=domain,
            task_domain=task_domain,
            availability_error=self.availability_error,
        )

    def _sync_index(self) -> None:
        if self.vector_store is None:
            return
        records = [self._vector_record(chunk) for chunk in self.source_store.chunks()]
        self.vector_store.upsert(records)

    def _index_source(self, source_id: str) -> int:
        if self.vector_store is None:
            return 0
        chunks = [
            chunk
            for chunk in self.source_store.chunks()
            if chunk.source_id == source_id
        ]
        self.vector_store.upsert(self._vector_record(chunk) for chunk in chunks)
        return len(chunks)

    def _vector_record(self, chunk: SourceChunk):
        from app.storage.vector_store import VectorRecord

        return VectorRecord(
            id=chunk.chunk_id,
            vector=self.embedder.embed(chunk.text),
            payload={
                "chunk_id": chunk.chunk_id,
                "source_id": chunk.source_id,
                "source_name": chunk.source_name,
                "index": chunk.index,
                "provenance": dict(chunk.provenance),
                "embedding_version": self.embedder.version,
            },
        )

    def _vector_count(self) -> int:
        if self.vector_store is None:
            return 0
        count = getattr(self.vector_store, "count", None)
        if not callable(count):
            return 0
        try:
            return max(0, int(count()))
        except (TypeError, ValueError, VectorBackendUnavailable):
            return 0


__all__ = ["KnowledgeBase"]
