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

    @classmethod
    def from_env(cls) -> "StorageConfig":
        backend = os.getenv("VECTOR_BACKEND", cls.vector_backend).strip().lower()
        if backend not in {"memory", "qdrant"}:
            raise ValueError(f"Unsupported VECTOR_BACKEND={backend}")

        vector_size = int(os.getenv("VECTOR_SIZE", str(cls.vector_size)))
        if vector_size < 1:
            raise ValueError("VECTOR_SIZE must be positive")

        return cls(
            sqlite_path=os.getenv("STORAGE_SQLITE_PATH", cls.sqlite_path).strip(),
            vector_backend=backend,
            qdrant_path=os.getenv("QDRANT_PATH", cls.qdrant_path).strip(),
            qdrant_collection=os.getenv(
                "QDRANT_COLLECTION", cls.qdrant_collection
            ).strip(),
            vector_size=vector_size,
        )

    def public_dict(self) -> dict[str, object]:
        return asdict(self)
