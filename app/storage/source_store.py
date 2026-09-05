from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from pathlib import Path

from app.core.types import SourceChunk
from app.retrieval.text import make_chunks, normalize_source_name, normalize_text


class SourceStore:
    def __init__(self, root: str = "data"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "sources.json"
        self._chunks: list[SourceChunk] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(
                f"source store is not valid UTF-8 JSON: {self.path}"
            ) from exc
        if not isinstance(raw, dict):
            raise ValueError("source store root must be a JSON object")
        items = raw.get("chunks", [])
        if not isinstance(items, list):
            raise ValueError("source store chunks must be a JSON array")

        loaded: list[SourceChunk] = []
        seen_ids: set[str] = set()
        for position, item in enumerate(items):
            if not isinstance(item, dict):
                raise ValueError(
                    f"source store chunk {position} must be a JSON object"
                )
            try:
                chunk = SourceChunk(**item)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"source store chunk {position} has an invalid shape"
                ) from exc
            self._validate_chunk(chunk, position=position)
            if chunk.chunk_id in seen_ids:
                raise ValueError(
                    f"source store contains duplicate chunk_id {chunk.chunk_id!r}"
                )
            seen_ids.add(chunk.chunk_id)
            loaded.append(chunk)
        self._chunks = loaded

    def _save(self) -> None:
        payload = json.dumps(
            {"chunks": [c.__dict__ for c in self._chunks]},
            ensure_ascii=False,
            indent=2,
        )
        temporary_path: str | None = None
        try:
            fd, temporary_path = tempfile.mkstemp(
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                dir=self.root,
                text=True,
            )
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self.path)
            temporary_path = None
        finally:
            if temporary_path is not None:
                try:
                    os.unlink(temporary_path)
                except FileNotFoundError:
                    pass

    @staticmethod
    def _validate_chunk(chunk: SourceChunk, *, position: int | None = None) -> None:
        label = f"chunk {position}" if position is not None else "chunk"
        if not isinstance(chunk.chunk_id, str) or not chunk.chunk_id.strip():
            raise ValueError(f"{label} chunk_id must be a non-empty string")
        if not isinstance(chunk.source_id, str) or not chunk.source_id.strip():
            raise ValueError(f"{label} source_id must be a non-empty string")
        if not isinstance(chunk.source_name, str) or not chunk.source_name.strip():
            raise ValueError(f"{label} source_name must be a non-empty string")
        if not isinstance(chunk.text, str):
            raise ValueError(f"{label} text must be a string")
        if (
            isinstance(chunk.index, bool)
            or not isinstance(chunk.index, int)
            or chunk.index < 0
        ):
            raise ValueError(f"{label} index must be a non-negative integer")
        if (
            isinstance(chunk.score, bool)
            or not isinstance(chunk.score, (int, float))
            or not math.isfinite(chunk.score)
        ):
            raise ValueError(f"{label} score must be a finite number")

    def import_text(self, source_name: str, text: str) -> dict:
        source_name = normalize_source_name(source_name)
        clean_text = normalize_text(text)
        if not source_name:
            raise ValueError("source_name must not be empty")
        if not clean_text:
            raise ValueError("text must not be empty")

        chunks = make_chunks(source_name, clean_text)
        existing_ids = {c.chunk_id for c in self._chunks}
        added = [c for c in chunks if c.chunk_id not in existing_ids]
        if added:
            previous_chunks = self._chunks
            self._chunks = [*previous_chunks, *added]
            try:
                self._save()
            except Exception:
                self._chunks = previous_chunks
                raise
        source_id = chunks[0].source_id if chunks else None
        return {
            "source_id": source_id,
            "source_name": source_name,
            "chunks_added": len(added),
            "total_chunks_for_source": len(chunks),
            "snapshot_id": self.snapshot_id(),
        }

    def chunks(self) -> list[SourceChunk]:
        # SourceChunk is mutable; copies keep callers from changing the index
        # without going through the persistence boundary.
        return [SourceChunk(**c.__dict__) for c in self._chunks]

    def list_sources(self) -> list[dict]:
        grouped: dict[str, dict] = {}
        for c in self._chunks:
            item = grouped.setdefault(c.source_id, {
                "source_id": c.source_id,
                "source_name": c.source_name,
                "chunk_count": 0,
            })
            item["chunk_count"] += 1
        return sorted(
            grouped.values(), key=lambda x: (x["source_name"], x["source_id"])
        )

    def source(self, source_id: str) -> dict | None:
        chunks = [c for c in self._chunks if c.source_id == source_id]
        if not chunks:
            return None
        chunks.sort(key=lambda c: c.index)
        return {
            "source_id": source_id,
            "source_name": chunks[0].source_name,
            "chunks": [c.__dict__ for c in chunks],
        }

    def chunk(self, chunk_id: str) -> dict | None:
        for c in self._chunks:
            if c.chunk_id == chunk_id:
                return c.__dict__.copy()
        return None

    def snapshot_id(self) -> str:
        payload = "\n".join(
            f"{c.chunk_id}\0{c.source_id}\0{c.source_name}\0{c.index}\0{c.text}"
            for c in sorted(self._chunks, key=lambda x: x.chunk_id)
        )
        return "corpus_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def clear(self) -> None:
        previous_chunks = self._chunks
        self._chunks = []
        try:
            self._save()
        except Exception:
            self._chunks = previous_chunks
            raise
