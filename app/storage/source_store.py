from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

from app.core.types import SourceChunk
from app.ingestion.documents import extract_document, extract_document_path
from app.ingestion.text import make_chunks, normalize_source_name, normalize_text


SOURCE_STORE_SCHEMA_VERSION = "kb-v2-source-store-v1"
LEGACY_INGESTION_VERSION = "legacy-source-store-v1"


class SourceStore:
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
        self._load_source_records(raw.get("sources"))

    def _load_source_records(self, raw_sources: object) -> None:
        """Load V2 document metadata while deriving a safe legacy view."""

        self._sources = {}
        for chunk in self._chunks:
            if chunk.source_id not in self._sources:
                self._sources[chunk.source_id] = self._legacy_source_record(chunk)
            if chunk.provenance:
                self._sources[chunk.source_id]["provenance"].update(
                    dict(chunk.provenance)
                )

        if raw_sources is None:
            return
        if isinstance(raw_sources, dict):
            records = list(raw_sources.values())
        elif isinstance(raw_sources, list):
            records = raw_sources
        else:
            raise ValueError("source store sources must be a JSON array or object")

        chunk_source_ids = {chunk.source_id for chunk in self._chunks}
        for position, raw_source in enumerate(records):
            if not isinstance(raw_source, Mapping):
                raise ValueError(
                    f"source store source {position} must be a JSON object"
                )
            record = dict(raw_source)
            source_id = record.get("source_id")
            source_name = record.get("source_name")
            if not isinstance(source_id, str) or not source_id.strip():
                raise ValueError(f"source store source {position} has no source_id")
            if not isinstance(source_name, str) or not source_name.strip():
                raise ValueError(f"source store source {position} has no source_name")
            if source_id not in chunk_source_ids:
                raise ValueError(
                    f"source store source {source_id!r} has no stored chunks"
                )
            provenance = record.get("provenance", {})
            if not isinstance(provenance, Mapping):
                raise ValueError(
                    f"source store source {source_id!r} provenance must be an object"
                )
            record["source_id"] = source_id.strip()
            record["source_name"] = normalize_source_name(source_name)
            record["provenance"] = dict(provenance)
            self._sources[record["source_id"]] = record

    def _save(self) -> None:
        payload = json.dumps(
            {
                "schema_version": SOURCE_STORE_SCHEMA_VERSION,
                "sources": [
                    self._copy_source_record(self._sources[source_id])
                    for source_id in sorted(self._sources)
                ],
                "chunks": [self._copy_chunk(c) for c in self._chunks],
            },
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
        if not isinstance(chunk.provenance, Mapping):
            raise ValueError(f"{label} provenance must be an object")

    @staticmethod
    def _copy_chunk(chunk: SourceChunk) -> dict[str, Any]:
        value = dict(chunk.__dict__)
        value["provenance"] = dict(chunk.provenance)
        return value

    @staticmethod
    def _copy_source_record(record: Mapping[str, Any]) -> dict[str, Any]:
        value = dict(record)
        if isinstance(value.get("provenance"), Mapping):
            value["provenance"] = dict(value["provenance"])
        return value

    @staticmethod
    def _legacy_source_record(chunk: SourceChunk) -> dict[str, Any]:
        return {
            "source_id": chunk.source_id,
            "source_name": chunk.source_name,
            "chunk_count": 0,
            "text_chars": 0,
            "source_hash": None,
            "source_version": None,
            "source_type": None,
            "source_format": None,
            "ingestion_version": LEGACY_INGESTION_VERSION,
            "provenance": {
                "source_id": chunk.source_id,
                "source_name": chunk.source_name,
                "ingestion_version": LEGACY_INGESTION_VERSION,
            },
        }

    @staticmethod
    def _provenance_input(provenance: Mapping[str, Any] | None) -> dict[str, Any]:
        if provenance is None:
            return {}
        if not isinstance(provenance, Mapping):
            raise TypeError("provenance must be an object")
        value = dict(provenance)
        try:
            json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("provenance must be JSON serializable") from exc
        return value

    def import_text(
        self,
        source_name: str,
        text: str,
        *,
        provenance: Mapping[str, Any] | None = None,
    ) -> dict:
        source_name = normalize_source_name(source_name)
        clean_text = normalize_text(text)
        if not source_name:
            raise ValueError("source_name must not be empty")
        if not clean_text:
            raise ValueError("text must not be empty")

        chunks = make_chunks(source_name, clean_text)
        if not chunks:
            raise ValueError("text must not be empty")
        source_id = chunks[0].source_id
        source_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()
        supplied_provenance = self._provenance_input(provenance)
        owner_id = supplied_provenance.get("owner_user_id")
        existing_source = self._sources.get(source_id)
        if existing_source is not None:
            existing_owner = existing_source.get("provenance", {}).get("owner_user_id")
            if existing_owner != owner_id:
                # Keep existing IDs intact; namespace only an actual cross-owner collision.
                owner_suffix = hashlib.sha256(
                    f"{source_id}\0{owner_id or ''}".encode("utf-8")
                ).hexdigest()[:16]
                source_id = f"{source_id}_{owner_suffix}"
                scoped_source = self._sources.get(source_id)
                if (
                    scoped_source is not None
                    and scoped_source.get("provenance", {}).get("owner_user_id") != owner_id
                ):
                    raise ValueError("source identity conflicts with another owner")
                chunks = [
                    replace(
                        chunk,
                        source_id=source_id,
                        chunk_id=f"{source_id}_c{chunk.index:04d}",
                    )
                    for chunk in chunks
                ]
        source_provenance = {
            **supplied_provenance,
            "source_id": source_id,
            "source_name": source_name,
            "source_hash": source_hash,
            "source_version": source_id,
        }
        chunk_provenance = [
            {
                **source_provenance,
                "chunk_id": chunk.chunk_id,
                "chunk_index": chunk.index,
            }
            for chunk in chunks
        ]
        chunks = [
            SourceChunk(
                **{
                    **chunk.__dict__,
                    "provenance": chunk_provenance[index],
                }
            )
            for index, chunk in enumerate(chunks)
        ]
        existing_ids = {c.chunk_id for c in self._chunks}
        added = [c for c in chunks if c.chunk_id not in existing_ids]
        source_record = {
            "source_id": source_id,
            "source_name": source_name,
            "chunk_count": len(chunks),
            "text_chars": len(clean_text),
            "source_hash": source_hash,
            "source_version": source_id,
            "source_type": supplied_provenance.get("source_type"),
            "source_format": supplied_provenance.get("source_format"),
            "ingestion_version": supplied_provenance.get(
                "ingestion_version", LEGACY_INGESTION_VERSION
            ),
            "provenance": source_provenance,
        }
        previous_chunks = self._chunks
        previous_sources = self._sources
        self._chunks = [*previous_chunks, *added]
        self._sources = {
            **previous_sources,
            source_id: source_record,
        }
        try:
            self._save()
        except Exception:
            self._chunks = previous_chunks
            self._sources = previous_sources
            raise
        return {
            "source_id": source_id,
            "source_name": source_name,
            "chunks_added": len(added),
            "total_chunks_for_source": len(chunks),
            "source_hash": source_hash,
            "source_version": source_id,
            "provenance": dict(source_provenance),
            "snapshot_id": self.snapshot_id(),
        }

    def import_document(
        self,
        source_name: str,
        data: bytes | str,
        *,
        origin: str = "upload",
        content_type: str | None = None,
        provenance: Mapping[str, Any] | None = None,
    ) -> dict:
        document = extract_document(
            data,
            source_name,
            origin=origin,
            content_type=content_type,
        )
        return self.import_text(
            document.source_name,
            document.text,
            provenance={**document.provenance, **(provenance or {})},
        )

    def import_path(self, path: str | Path) -> dict:
        document = extract_document_path(path)
        return self.import_text(
            document.source_name,
            document.text,
            provenance=document.provenance,
        )

    def chunks(self) -> list[SourceChunk]:
        # SourceChunk is mutable; copies keep callers from changing the index
        # without going through the persistence boundary.
        return [
            SourceChunk(
                **{
                    **c.__dict__,
                    "provenance": dict(c.provenance),
                }
            )
            for c in self._chunks
        ]

    def list_sources(self) -> list[dict]:
        grouped = {
            source_id: self._copy_source_record(record)
            for source_id, record in self._sources.items()
        }
        for chunk in self._chunks:
            grouped.setdefault(chunk.source_id, self._legacy_source_record(chunk))
        # Recount from canonical chunks so a manually edited metadata record
        # cannot make the management view disagree with searchable content.
        counts: dict[str, int] = {}
        for chunk in self._chunks:
            counts[chunk.source_id] = counts.get(chunk.source_id, 0) + 1
        for source_id, count in counts.items():
            grouped[source_id]["chunk_count"] = count
        return sorted(
            grouped.values(), key=lambda x: (x["source_name"], x["source_id"])
        )

    def source(self, source_id: str) -> dict | None:
        chunks = [c for c in self._chunks if c.source_id == source_id]
        if not chunks:
            return None
        chunks.sort(key=lambda c: c.index)
        metadata = self._copy_source_record(
            self._sources.get(source_id, self._legacy_source_record(chunks[0]))
        )
        return {
            "source_id": source_id,
            "source_name": chunks[0].source_name,
            "provenance": metadata.get("provenance", {}),
            "metadata": metadata,
            "chunks": [self._copy_chunk(c) for c in chunks],
        }

    def chunk(self, chunk_id: str) -> dict | None:
        for c in self._chunks:
            if c.chunk_id == chunk_id:
                return self._copy_chunk(c)
        return None

    def status(self) -> dict[str, Any]:
        """Return bounded management metadata for the current local corpus."""

        return {
            "schema_version": SOURCE_STORE_SCHEMA_VERSION,
            "snapshot_id": self.snapshot_id(),
            "source_count": len(self._sources),
            "chunk_count": len(self._chunks),
            "text_chars": sum(len(chunk.text) for chunk in self._chunks),
        }

    def snapshot_id(self) -> str:
        payload = "\n".join(
            f"{c.chunk_id}\0{c.source_id}\0{c.source_name}\0{c.index}\0{c.text}"
            for c in sorted(self._chunks, key=lambda x: x.chunk_id)
        )
        return "corpus_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def clear(self) -> None:
        previous_chunks = self._chunks
        previous_sources = self._sources
        self._chunks = []
        self._sources = {}
        try:
            self._save()
        except Exception:
            self._chunks = previous_chunks
            self._sources = previous_sources
            raise
