from __future__ import annotations

import os
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class StorageConfig:
    """Local persistence settings kept separate from research/runtime settings.

    The Qdrant client is intentionally not imported here.  This lets callers
    validate configuration and use the SQLite boundary without making Qdrant a
    mandatory dependency for the current M0 candidate.
    """

    sqlite_path: str = "storage/metadata.sqlite3"
    vector_backend: str = "qdrant"
    qdrant_path: str = "storage/qdrant"
    qdrant_collection: str = "domain"
    vector_size: int = 768
    retrieval_mode: str = "LEXICAL"
    embedding_provider: str = "hash"
    embedding_model: str = "nomic-embed-text"

    @classmethod
    def from_env(cls) -> "StorageConfig":
        raw_mode = os.getenv("RETRIEVAL_MODE", "").strip().upper()
        if not raw_mode:
            raw_mode = "VECTOR" if os.getenv("VECTOR_BACKEND", "").strip() else cls.retrieval_mode
        if raw_mode not in {"LEXICAL", "VECTOR", "HYBRID"}:
            raise ValueError(f"Unsupported RETRIEVAL_MODE={raw_mode}")

        backend_value = os.getenv("VECTOR_BACKEND", "").strip().lower()
        backend = backend_value or cls.vector_backend
        if backend not in {"memory", "qdrant"}:
            raise ValueError(f"Unsupported VECTOR_BACKEND={backend}")

        vector_size = int(os.getenv("VECTOR_SIZE", str(cls.vector_size)))
        if vector_size < 1:
            raise ValueError("VECTOR_SIZE must be positive")
        embedding_provider = os.getenv(
            "EMBEDDING_PROVIDER", cls.embedding_provider
        ).strip().lower()
        if embedding_provider not in {"hash", "ollama"}:
            raise ValueError(f"Unsupported EMBEDDING_PROVIDER={embedding_provider}")

        return cls(
            sqlite_path=os.getenv("STORAGE_SQLITE_PATH", cls.sqlite_path).strip(),
            retrieval_mode=raw_mode,
            vector_backend=backend,
            qdrant_path=os.getenv("QDRANT_PATH", cls.qdrant_path).strip(),
            qdrant_collection=os.getenv(
                "QDRANT_COLLECTION", cls.qdrant_collection
            ).strip(),
            vector_size=vector_size,
            embedding_provider=embedding_provider,
            embedding_model=os.getenv(
                "LOCAL_EMBEDDING_MODEL", cls.embedding_model
            ).strip(),
        )

    def public_dict(self) -> dict[str, object]:
        return asdict(self)
