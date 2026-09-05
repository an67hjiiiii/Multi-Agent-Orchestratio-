from __future__ import annotations
import hashlib
import json
from pathlib import Path
from app.core.types import SourceChunk
from app.retrieval.text import make_chunks

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
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        self._chunks = [SourceChunk(**item) for item in raw.get("chunks", [])]

    def _save(self) -> None:
        self.path.write_text(json.dumps({"chunks": [c.__dict__ for c in self._chunks]}, ensure_ascii=False, indent=2), encoding="utf-8")

    def import_text(self, source_name: str, text: str) -> dict:
        chunks = make_chunks(source_name, text)
        existing_ids = {c.chunk_id for c in self._chunks}
        added = [c for c in chunks if c.chunk_id not in existing_ids]
        self._chunks.extend(added)
        self._save()
        source_id = chunks[0].source_id if chunks else None
        return {
            "source_id": source_id,
            "source_name": source_name,
            "chunks_added": len(added),
            "total_chunks_for_source": len(chunks),
            "snapshot_id": self.snapshot_id(),
        }

    def chunks(self) -> list[SourceChunk]:
        return list(self._chunks)

    def list_sources(self) -> list[dict]:
        grouped: dict[str, dict] = {}
        for c in self._chunks:
            item = grouped.setdefault(c.source_id, {
                "source_id": c.source_id,
                "source_name": c.source_name,
                "chunk_count": 0,
            })
            item["chunk_count"] += 1
        return sorted(grouped.values(), key=lambda x: (x["source_name"], x["source_id"]))

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
        self._chunks = []
        self._save()
