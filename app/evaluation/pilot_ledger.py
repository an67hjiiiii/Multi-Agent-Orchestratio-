"""Durable, single-writer ledger for an approved future pilot run."""
from __future__ import annotations

import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

METRIC_SCHEMA_VERSION = "m1-metric-contract-v1"


class PilotLockedError(RuntimeError):
    pass


def canonical_metric_snapshot(
    *, status: str, condition: str | None, metrics: dict | None, events: list | None
) -> dict[str, object]:
    """Materialize the frozen automated metric contract beside one attempt.

    This captures only structural/provider telemetry. Gold-dependent metrics
    remain outside the canonical runtime record and are joined after review.
    """

    raw = metrics if isinstance(metrics, dict) else {}
    task_events = [item for item in (events or []) if isinstance(item, dict) and item.get("stage") == "task_retrieval"]
    selected_count = sum(len(item.get("selected", [])) for item in task_events if isinstance(item.get("selected"), list))
    shared_count = sum(len(item.get("shared_evidence_ids", [])) for item in task_events if isinstance(item.get("shared_evidence_ids"), list))
    normalization = next((item for item in (events or []) if isinstance(item, dict) and item.get("stage") == "normalization"), None)
    removed = normalization.get("removed") if isinstance(normalization, dict) else None
    after = normalization.get("tasks") if isinstance(normalization, dict) else None
    task_count_after = len(after) if isinstance(after, list) else None
    failure = next((item for item in (events or []) if isinstance(item, dict) and item.get("stage") in {"run_failed", "runner_failed"}), None)
    return {
        "schema_version": METRIC_SCHEMA_VERSION,
        "terminal_status": status,
        "llm_calls": raw.get("llm_calls"),
        "input_tokens": raw.get("input_tokens"),
        "output_tokens": raw.get("output_tokens"),
        "total_tokens": raw.get("total_tokens"),
        "latency_ms": raw.get("latency_ms"),
        "retrieval_latency_ms": raw.get("retrieval_latency_ms"),
        "generation_latency_ms": raw.get("generation_latency_ms"),
        "peak_rss_mb": raw.get("peak_rss_mb"),
        "gpu_memory_mb": raw.get("gpu_memory_mb"),
        "context_tokens_est": raw.get("context_tokens_est"),
        "context_chars": raw.get("context_chars"),
        "retrieved_chunks": raw.get("retrieved_chunks"),
        "selected_chunks": raw.get("selected_chunks"),
        "dropped_chunks": raw.get("dropped_chunks"),
        "citations_emitted": raw.get("citations_emitted"),
        "citations_valid": raw.get("citations_valid"),
        "citation_locator_validity": raw.get("citation_locator_validity"),
        "duplicate_tasks_removed": removed if condition == "C" else None,
        "duplicate_task_rate": (
            removed / (task_count_after + removed)
            if condition == "C" and isinstance(removed, int) and isinstance(task_count_after, int) and task_count_after + removed > 0
            else None
        ),
        "overlap_reuse_ratio": shared_count / selected_count if condition == "C" and selected_count else None,
        "failure_stage": failure.get("stage") if failure else None,
        "retry_count": "NOT_RECORDED",
    }


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
        if "metric_snapshot" not in record:
            record = {
                **record,
                "metric_snapshot": canonical_metric_snapshot(
                    status=str(record.get("status", "")),
                    condition=record.get("condition") if isinstance(record.get("condition"), str) else None,
                    metrics=record.get("metrics") if isinstance(record.get("metrics"), dict) else None,
                    events=record.get("events") if isinstance(record.get("events"), list) else None,
                ),
            }
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
