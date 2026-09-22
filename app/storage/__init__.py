from __future__ import annotations

from app.storage.sqlite_store import SQLiteMetadataStore, SQLiteStore
from app.storage.vector_store import (
    InMemoryVectorStore,
    QdrantStore,
    QdrantVectorStore,
    VectorBackendUnavailable,
    VectorMatch,
    VectorRecord,
    VectorStore,
)

__all__ = [
    "InMemoryVectorStore",
    "KnowledgeBase",
    "QdrantStore",
    "QdrantVectorStore",
    "SQLiteMetadataStore",
    "SQLiteStore",
    "VectorBackendUnavailable",
    "VectorMatch",
    "VectorRecord",
    "VectorStore",
]


def __getattr__(name: str):
    """Retain the package-level KnowledgeBase export without an import cycle."""

    if name == "KnowledgeBase":
        from app.storage.knowledge_base import KnowledgeBase

        return KnowledgeBase
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
