"""Reusable serial runner and post-inference evaluator for the final six conditions.

This module deliberately keeps generation and gold evaluation separate.  The
runner receives only case ids and requests; a gold loader is called by the
evaluator after every generation record is terminal.  It is therefore safe to
use this harness for dry-run and FakeProvider plumbing checks without leaking
gold data into the runtime.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping

from app.evaluation.pilot_ledger import PilotLockedError

FINAL_CONDITIONS = ("A", "B", "C", "C-P", "C-N", "C-O")
TERMINAL_STATUSES = frozenset({"COMPLETE", "PARTIAL", "NO_EVIDENCE", "FAILED"})
PENDING_HUMAN_APPROVAL = "PENDING_HUMAN_APPROVAL"
APPROVED = "APPROVED"
LEDGER_SCHEMA = "final-six-condition-ledger-v1"
REPORT_SCHEMA = "final-six-condition-report-v1"
EVALUATION_SCHEMA = "final-six-condition-evaluation-v1"


class LaunchBlockedError(RuntimeError):
    """Raised when the owner has not approved the dataset and semantic gold."""


@dataclass(frozen=True)
class FinalCase:
    case_id: str
    query: str
    kind: str = ""


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _condition_definitions() -> dict[str, dict[str, Any]]:
    """Read the checked-in condition table without importing runtime adapters."""

    path = Path(__file__).resolve().parents[2] / "config" / "conditions.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {condition: dict(payload[condition]) for condition in FINAL_CONDITIONS}


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_cases(path: str | Path) -> list[FinalCase]:
    """Load request-only cases; gold-shaped fields are rejected at the seam."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("final cases manifest must be a JSON object")
    schema_version = payload.get("schema_version")
    if schema_version == "final-experiment-cases-v1":
        raw_cases = payload.get("cases")
    elif schema_version == "m1-final-frozen-requests-v1":
        # The canonical frozen manifest groups four request variants under
        # each scenario. Flatten only request fields at the generation seam.
        raw_cases = []
        for group in payload.get("scenario_groups") or []:
            if not isinstance(group, dict):
                raise ValueError("final scenario groups must be objects")
            for variant in group.get("variants") or []:
                if not isinstance(variant, dict):
                    raise ValueError("final scenario variants must be objects")
                raw_cases.append(
                    {
                        "id": variant.get("case_id"),
                        "query": variant.get("request_text"),
                        "kind": group.get("canonical_domain") or "",
                    }
                )
    else:
        raise ValueError(
            "final cases must use schema_version final-experiment-cases-v1 "
            "or m1-final-frozen-requests-v1"
        )
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError("final cases must contain a non-empty cases list")
    forbidden = {"gold", "gold_answer", "expected_answer", "rubric", "expected_evidence"}
    cases: list[FinalCase] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_cases, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"case {index} must be an object")
        if forbidden.intersection(raw):
            raise ValueError(f"case {index} contains gold/evaluation fields")
        case_id = raw.get("id")
        query = raw.get("query")
        if not isinstance(case_id, str) or not case_id.strip() or case_id in seen:
            raise ValueError(f"case {index} has a missing or duplicate id")
        if not isinstance(query, str) or not query.strip():
            raise ValueError(f"case {case_id} must have a non-empty query")
        seen.add(case_id)
        cases.append(FinalCase(case_id=case_id, query=query, kind=str(raw.get("kind") or "")))
    return cases


def build_effective_config(
    runtime: Any,
    *,
    experiment_id: str,
    experiment_freeze_id: str,
    manifest_sha256: str,
    source_snapshot_id: str,
    prompt_version: str = "final-runner-v1",
) -> dict[str, Any]:
    """Create the immutable, hash-addressed config recorded on every attempt."""

    payload: dict[str, Any] = {
        "schema_version": "final-effective-config-v1",
        "experiment_id": experiment_id,
        "experiment_freeze_id": experiment_freeze_id,
        "manifest_sha256": manifest_sha256,
        "source_snapshot_id": source_snapshot_id,
        "prompt_version": prompt_version,
        "runtime": runtime.public_dict(),
        "conditions": _condition_definitions(),
    }
    config_hash = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    return {**copy.deepcopy(payload), "config_hash": config_hash}


def stable_attempt_id(experiment_id: str, case_id: str, condition: str, repeat: int, config_hash: str) -> str:
    value = f"{experiment_id}|{case_id}|{condition}|repeat-{repeat}|{config_hash}"
    return "attempt_" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]


def assert_launch_approved(dataset_status: str, gold_status: str) -> None:
    if dataset_status != APPROVED or gold_status != APPROVED:
        raise LaunchBlockedError(
            "final experiment launch blocked: dataset and semantic gold require "
            f"{APPROVED}; got dataset={dataset_status!r}, gold={gold_status!r}"
        )


@contextmanager
def single_writer_lock(output_dir: Path) -> Iterator[None]:
    """Use a narrow lock so two resumptions cannot append concurrently."""

    output_dir.mkdir(parents=True, exist_ok=True)
    lock_path = output_dir / ".final-experiment.lock"
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise PilotLockedError(f"final experiment output is already locked: {lock_path}") from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(str(os.getpid()))
            handle.flush()
            os.fsync(handle.fileno())
        yield
    finally:
        lock_path.unlink(missing_ok=True)


class FinalAttemptLedger:
    """Append-only JSONL ledger with stable canonical keys and identity checks."""

    def __init__(self, path: str | Path, identity: Mapping[str, Any]):
        self.path = Path(path)
        self.identity = dict(identity)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._identity_path = self.path.with_name(self.path.name + ".identity.json")
        if self._identity_path.exists():
            existing = json.loads(self._identity_path.read_text(encoding="utf-8"))
            if existing != self.identity:
                raise ValueError("final ledger identity does not match this manifest/configuration")
        else:
            self._identity_path.write_text(json.dumps(self.identity, sort_keys=True) + "\n", encoding="utf-8")

    def records(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        records: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(json.loads(line))
        return records

    def canonical_keys(self) -> set[str]:
        return {str(item["key"]) for item in self.records() if item.get("classification") == "canonical_attempt"}

    def append_terminal(self, record: Mapping[str, Any]) -> dict[str, Any]:
        status = str(record.get("status") or "")
        if status not in TERMINAL_STATUSES:
            raise ValueError(f"only terminal statuses may be persisted: {status!r}")
        key = str(record.get("key") or "")
        if not key:
            raise ValueError("terminal record requires a stable key")
        classification = "duplicate_attempt" if key in self.canonical_keys() else "canonical_attempt"
        enriched = {**copy.deepcopy(dict(record)), "classification": classification, "ledger_schema": LEDGER_SCHEMA}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(enriched, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return enriched

    def report(self) -> dict[str, Any]:
        records = self.records()
        return {
            "report_schema": REPORT_SCHEMA,
            "identity": copy.deepcopy(self.identity),
            "run_count": sum(item.get("classification") == "canonical_attempt" for item in records),
            "rows": [item for item in records if item.get("classification") == "canonical_attempt"],
            "attempt_count": len(records),
            "inference_complete": all(item.get("status") in TERMINAL_STATUSES for item in records),
            "human_grading": "PENDING",
        }


def _runner_failure(case: FinalCase, condition: str, repeat: int, exc: Exception) -> dict[str, Any]:
    return {
        "case_id": case.case_id,
        "kind": case.kind,
        "condition": condition,
        "repeat": repeat,
        "status": "FAILED",
        "run_id": "",
        "answer": "",
        "metrics": {},
        "events": [{"stage": "runner_failed", "error_type": type(exc).__name__}],
        "tasks": [],
        "task_results": [],
        "effective_config": {},
    }


async def run_final_experiment(
    *,
    cases_path: str | Path,
    output_dir: str | Path,
    runs_dir: str | Path,
    provider: str = "fake",
    experiment_id: str = "final-six-condition-v1",
    experiment_freeze_id: str = "PENDING_HUMAN_APPROVAL",
    dataset_status: str = PENDING_HUMAN_APPROVAL,
    gold_status: str = PENDING_HUMAN_APPROVAL,
    source_snapshot_id: str = "provided-at-launch",
    repeats: int = 1,
    conditions: tuple[str, ...] = FINAL_CONDITIONS,
    pipeline_factory: Callable[[Path], Any] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run requests serially, checkpointing one terminal attempt at a time."""

    if provider not in {"fake", "ollama"}:
        raise ValueError("provider must be fake or ollama")
    if repeats < 1:
        raise ValueError("repeats must be at least 1")
    if not conditions or any(condition not in FINAL_CONDITIONS for condition in conditions):
        raise ValueError("conditions must be a non-empty subset of the final six conditions")
    if len(set(conditions)) != len(conditions):
        raise ValueError("conditions must not repeat")

    plan = {
        "experiment_id": experiment_id,
        "conditions": list(conditions),
        "repeats": repeats,
        "provider": provider,
        "dataset_status": dataset_status,
        "gold_status": gold_status,
        "launch_status": "READY" if dataset_status == APPROVED and gold_status == APPROVED else "BLOCKED",
        "generation_contract": "serial; concurrency=1; no automatic retry",
    }
    if dry_run:
        if plan["launch_status"] == "BLOCKED":
            plan["block_reason"] = "dataset/gold approval is PENDING_HUMAN_APPROVAL"
        return {"plan": plan, "report": None, "path": None}
    assert_launch_approved(dataset_status, gold_status)

    cases = load_cases(cases_path)
    output_path = Path(output_dir)
    manifest_sha = sha256_file(cases_path)
    prior_env = {key: os.environ.get(key) for key in ("IMPLEMENTATION_PROFILE", "PROVIDER")}
    os.environ["IMPLEMENTATION_PROFILE"] = "m2"
    os.environ["PROVIDER"] = provider
    try:
        # Keep the dry-run path dependency-light; runtime adapters are loaded
        # only after explicit approval permits generation.
        from app.core.config import RuntimeConfig

        runtime = RuntimeConfig.from_env()
        for condition in conditions:
            runtime.assert_condition(condition)
        effective = build_effective_config(
            runtime,
            experiment_id=experiment_id,
            experiment_freeze_id=experiment_freeze_id,
            manifest_sha256=manifest_sha,
            source_snapshot_id=source_snapshot_id,
        )
        identity = {
            "experiment_id": experiment_id,
            "manifest_sha256": manifest_sha,
            "provider": provider,
            "model": runtime.local_model,
            "config_hash": effective["config_hash"],
            "experiment_freeze_id": experiment_freeze_id,
        }
        ledger_path = output_path / "canonical_attempt_ledger.jsonl"
        with single_writer_lock(output_path):
            ledger = FinalAttemptLedger(ledger_path, identity)
            pipeline = pipeline_factory(Path(runs_dir)) if pipeline_factory else _default_pipeline(runs_dir)
            for case in cases:
                for repeat in range(1, repeats + 1):
                    for condition in conditions:
                        key = f"{case.case_id}|{condition}|repeat-{repeat}"
                        if key in ledger.canonical_keys():
                            continue
                        try:
                            run = await pipeline.run(case.query, condition, provider)
                            if not isinstance(run, dict):
                                raise TypeError("pipeline result must be an object")
                        except Exception as exc:
                            run = _runner_failure(case, condition, repeat, exc)
                        status = str(run.get("status") or "FAILED").upper()
                        if status not in TERMINAL_STATUSES:
                            run = _runner_failure(case, condition, repeat, ValueError("non-terminal pipeline status"))
                        record = {
                            "attempt_id": stable_attempt_id(experiment_id, case.case_id, condition, repeat, effective["config_hash"]),
                            "key": key,
                            "case_id": case.case_id,
                            "kind": case.kind,
                            "condition": condition,
                            "repeat": repeat,
                            "status": str(run.get("status") or "FAILED").upper(),
                            "run_id": str(run.get("run_id") or ""),
                            "answer": str(run.get("answer") or ""),
                            "metrics": copy.deepcopy(run.get("metrics") or {}),
                            "events": copy.deepcopy(run.get("events") or []),
                            "tasks": copy.deepcopy(run.get("tasks") or []),
                            "task_results": copy.deepcopy(run.get("task_results") or []),
                            "effective_config": copy.deepcopy(effective),
                            "inference_only": True,
                            "terminal_recorded_at": datetime.now(timezone.utc).isoformat(),
                        }
                        ledger.append_terminal(record)
            report = ledger.report()
            report_path = output_path / "final_six_condition_report.json"
            temporary = report_path.with_suffix(".json.tmp")
            temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            temporary.replace(report_path)
        return {"plan": plan, "report": report, "path": report_path}
    finally:
        for key, value in prior_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _default_pipeline(runs_dir: str | Path) -> Any:
    # Keep dry-run dependency-light; compose runtime services only after the
    # explicit launch-approval gate has passed.
    from app.research.runtime_factory import build_pipeline_from_corpus

    return build_pipeline_from_corpus(
        data_dir=Path(runs_dir).parent / "data",
        runs_dir=runs_dir,
    )


def evaluate_after_inference(
    report_path: str | Path,
    gold_loader: Callable[[], Any],
    *,
    scorer: Callable[[dict[str, Any], Any], Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Load gold only after the persisted report proves inference is terminal."""

    report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    rows = report.get("rows")
    if (
        not report.get("inference_complete")
        or not isinstance(rows, list)
        or not rows
        or any(not isinstance(row, dict) or row.get("status") not in TERMINAL_STATUSES for row in rows)
    ):
        raise ValueError("cannot evaluate before all generation attempts are terminal")
    # This is intentionally the first point at which gold is touched.
    gold = gold_loader()
    evaluations = []
    for row in rows:
        result = dict(scorer(row, gold) if scorer else {})
        evaluations.append({"attempt_id": row.get("attempt_id"), "case_id": row.get("case_id"), "condition": row.get("condition"), **result})
    return {
        "evaluation_schema": EVALUATION_SCHEMA,
        "report_path": str(report_path),
        "gold_loaded_after_inference": True,
        "human_grading": "PENDING",
        "rows": evaluations,
    }
