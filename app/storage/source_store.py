from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from app.core.types import SourceChunk
from app.retrieval.text import make_chunks, normalize_text


SOURCE_STORE_SCHEMA_VERSION = "s2-source-store-v1"


class SourceStore:
    """Owner-local file store for isolated test/demo use.

    PostgreSQL remains the production source of truth.  This store keeps the
    same source/chunk provenance shape for the explicit file backend.
    """

    def __init__(self, root: str = "data"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "sources.json"
        self._chunks: list[SourceChunk] = []
        self._sources: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        self._chunks = [SourceChunk(**item) for item in raw.get("chunks", [])]
        self._sources = {}
        for chunk in self._chunks:
            self._sources.setdefault(
                chunk.source_id,
                {
                    "source_id": chunk.source_id,
                    "source_name": chunk.source_name,
                    "provenance": dict(chunk.provenance),
                },
            )
        for item in raw.get("sources", []) or []:
            if isinstance(item, Mapping) and item.get("source_id"):
                record = dict(item)
                record["provenance"] = dict(record.get("provenance") or {})
                self._sources[str(record["source_id"])] = record

    def _save(self) -> None:
        self.path.write_text(
            json.dumps(
                {
                    "schema_version": SOURCE_STORE_SCHEMA_VERSION,
                    "sources": list(self._sources.values()),
                    "chunks": [c.__dict__ for c in self._chunks],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def import_text(
        self,
        source_name: str,
        text: str,
        *,
        provenance: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        clean_name = str(source_name or "").strip()
        clean_text = normalize_text(text)
        if not clean_name:
            raise ValueError("source_name must not be empty")
        if not clean_text:
            raise ValueError("text must not be empty")

        chunks = make_chunks(clean_name, clean_text)
        if not chunks:
            raise ValueError("text must not be empty")
        source_id = chunks[0].source_id
        source_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()
        source_provenance = {
            **dict(provenance or {}),
            "source_id": source_id,
            "source_name": clean_name,
            "source_hash": source_hash,
            "source_version": source_id,
        }
        chunks = [
            SourceChunk(
                **{
                    **chunk.__dict__,
                    "provenance": {
                        **source_provenance,
                        "chunk_id": chunk.chunk_id,
                        "chunk_index": chunk.index,
                    },
                }
            )
            for chunk in chunks
        ]
        existing_ids = {c.chunk_id for c in self._chunks}
        added = [c for c in chunks if c.chunk_id not in existing_ids]
        self._chunks.extend(added)
        self._sources[source_id] = {
            "source_id": source_id,
            "source_name": clean_name,
            "status": "READY",
            "chunk_count": len(chunks),
            "text_chars": len(clean_text),
            "source_hash": source_hash,
            "source_version": source_id,
            "provenance": source_provenance,
        }
        self._save()
        return {
            "source_id": source_id,
            "source_name": clean_name,
            "chunks_added": len(added),
            "total_chunks_for_source": len(chunks),
            "source_hash": source_hash,
            "source_version": source_id,
            "provenance": dict(source_provenance),
            "snapshot_id": self.snapshot_id(),
        }

    def chunks(self, source_ids: list[str] | None = None) -> list[SourceChunk]:
        selected = None if source_ids is None else set(source_ids)
        return [
            SourceChunk(**{**c.__dict__, "provenance": dict(c.provenance)})
            for c in self._chunks
            if (selected is None or c.source_id in selected)
            and self._sources.get(c.source_id, {}).get("status", "READY") == "READY"
        ]

    def list_sources(self) -> list[dict]:
        grouped: dict[str, dict] = {}
        for c in self._chunks:
            item = grouped.setdefault(
                c.source_id,
                {
                    "source_id": c.source_id,
                    "source_name": c.source_name,
                    "chunk_count": 0,
                },
            )
            item["chunk_count"] += 1
        return sorted(grouped.values(), key=lambda x: (x["source_name"], x["source_id"]))

    def source(self, source_id: str) -> dict | None:
        chunks = [c for c in self._chunks if c.source_id == source_id]
        if not chunks:
            return None
        chunks.sort(key=lambda c: c.index)
        metadata = dict(self._sources.get(source_id) or {})
        return {
            "source_id": source_id,
            "source_name": chunks[0].source_name,
            "provenance": dict(metadata.get("provenance") or chunks[0].provenance),
            "metadata": metadata,
            "status": metadata.get("status", "READY"),
            "chunks": [
                {**c.__dict__, "provenance": dict(c.provenance)} for c in chunks
            ],
        }

    def chunk(self, chunk_id: str) -> dict | None:
        for c in self._chunks:
            if c.chunk_id == chunk_id:
                return {**c.__dict__, "provenance": dict(c.provenance)}
        return None

    def snapshot_id(self) -> str:
        payload = "\n".join(
            f"{c.chunk_id}\0{c.source_id}\0{c.source_name}\0{c.index}\0{c.text}"
            for c in sorted(self._chunks, key=lambda x: x.chunk_id)
        )
        return "corpus_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def validate_source_selection(self, source_ids: list[str]) -> None:
        owned = {
            source_id
            for source_id, metadata in self._sources.items()
            if metadata.get("status", "READY") == "READY"
        }
        missing = [source_id for source_id in source_ids if source_id not in owned]
        if missing:
            raise LookupError("source not found")

    def mark_failed(self, source_id: str, error: Exception | str) -> None:
        metadata = self._sources.get(source_id)
        if metadata is None:
            return
        metadata.update(
            {
                "status": "FAILED",
                "error_type": type(error).__name__
                if isinstance(error, Exception)
                else "IngestionError",
                "error": str(error),
            }
        )
        self._save()

    def clear(self) -> None:
        self._chunks = []
        self._sources = {}
        self._save()
