from __future__ import annotations

from typing import Any, Iterable

from app.retrieval.embeddings import LocalHashEmbedder, TextEmbedder
from app.storage.vector_store import VectorMatch, VectorRecord, VectorStore


class IndexingError(RuntimeError):
    """A derived-index write failed; the authoritative source remains separate."""


class CandidateIndex:
    """Build/search a derived vector index from an owner-scoped source store."""

    def __init__(
        self,
        source_store: Any,
        vector_store: VectorStore,
        *,
        owner_user_id: str,
        embedder: TextEmbedder | None = None,
    ) -> None:
        if not isinstance(owner_user_id, str) or not owner_user_id.strip():
            raise ValueError("owner_user_id must be non-empty")
        self.source_store = source_store
        self.vector_store = vector_store
        self.owner_user_id = owner_user_id
        self.embedder = embedder or LocalHashEmbedder()

    def index_source(self, source_id: str) -> dict[str, Any]:
        source = self.source_store.source(source_id)
        if source is None:
            raise LookupError("source not found")
        if source.get("status") not in {None, "READY"}:
            raise IndexingError("only READY sources may be indexed")
        chunks = self.source_store.chunks([source_id])
        records = [
            VectorRecord(
                id=chunk.chunk_id,
                vector=self.embedder.embed(chunk.text),
                payload={
                    "owner_user_id": self.owner_user_id,
                    "source_id": chunk.source_id,
                    "chunk_id": chunk.chunk_id,
                    "source_name": chunk.source_name,
                    "embedding_version": self.embedder.version,
                    **dict(chunk.provenance),
                },
            )
            for chunk in chunks
        ]
        try:
            self.vector_store.upsert(records)
        except Exception as exc:
            marker = getattr(self.source_store, "mark_failed", None)
            if callable(marker):
                marker(source_id, exc)
            raise IndexingError("derived index write failed") from exc
        return {
            "source_id": source_id,
            "chunks_indexed": len(records),
            "embedding_version": self.embedder.version,
        }

    def candidates(
        self,
        query: str,
        *,
        limit: int = 10,
        source_ids: Iterable[str] | None = None,
    ) -> list[VectorMatch]:
        selected = None if source_ids is None else [str(source_id) for source_id in source_ids]
        return self.vector_store.search(
            self.embedder.embed(query),
            limit=limit,
            owner_user_id=self.owner_user_id,
            source_ids=selected,
        )


__all__ = ["CandidateIndex", "IndexingError"]
