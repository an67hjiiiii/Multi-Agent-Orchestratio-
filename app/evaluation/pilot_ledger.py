"""Durable, single-writer ledger for an approved future pilot run."""
from __future__ import annotations

import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


class PilotLockedError(RuntimeError):
    pass


class PilotLedger:
    """Atomic snapshots whose records only ever append in logical order."""

    def __init__(self, path: Path, identity: dict[str, object]):
        self.path, self.identity = path, identity
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load_or_create()

    def _load_or_create(self) -> dict:
        if not self.path.exists():
            return {"schema_version": "pilot-ledger-v1", "identity": self.identity, "attempts": []}
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if data.get("identity") != self.identity:
            raise ValueError("pilot ledger identity does not match this manifest/configuration")
        return data

    def canonical_keys(self) -> set[str]:
        return {item["key"] for item in self.data["attempts"] if item["classification"] == "canonical_attempt"}

    def append(self, record: dict[str, object]) -> None:
        key = record["key"]
        classification = "duplicate_attempt" if key in self.canonical_keys() else "canonical_attempt"
        self.data["attempts"].append({**record, "classification": classification})
        fd, temporary = tempfile.mkstemp(prefix=self.path.name + ".", dir=self.path.parent, text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(self.data, handle, ensure_ascii=False, indent=2)
                handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary): os.unlink(temporary)

    def report(self) -> dict[str, object]:
        canonical = [item for item in self.data["attempts"] if item["classification"] == "canonical_attempt"]
        return {"schema_version": "m1-pilot-report-v2", "identity": self.identity, "run_count": len(canonical), "rows": canonical, "human_grading": "PENDING"}


@contextmanager
def single_writer_lock(output_dir: Path) -> Iterator[None]:
    path = output_dir / ".pilot.lock"; output_dir.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise PilotLockedError(f"pilot output is already locked: {path}") from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(str(os.getpid())); handle.flush(); os.fsync(handle.fileno())
        yield
    finally:
        path.unlink(missing_ok=True)


def propose_raw_mapping(raw_runs: list[dict]) -> list[dict[str, object]]:
    """Read-only proposal; callers decide whether historical attempts become canonical."""
    seen: set[str] = set(); proposal = []
    for run in sorted(raw_runs, key=lambda item: str(item.get("created_at", ""))):
        key = f"{run.get('query')}|{run.get('condition')}"
        proposal.append({"run_id": run.get("run_id"), "key": key, "proposed_classification": "duplicate_attempt" if key in seen else "raw_attempt_requires_owner_rule"})
        seen.add(key)
    return proposal
