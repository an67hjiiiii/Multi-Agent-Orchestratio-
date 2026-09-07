"""Serial, frozen-manifest M1 A/B/C structural pilot runner."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from contextlib import contextmanager
from pathlib import Path

from app.core.config import RuntimeConfig
from app.evaluation.pilot_ledger import PilotLedger, single_writer_lock
from app.research.pipeline import ResearchPipeline
from app.storage.run_store import RunStore
from scripts.run_m0_calibration import prepare_store

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = ROOT / "datasets" / "pilot" / "m1_dev_cases.json"
EXPERIMENT_ID = "m1-pilot-authorized-v1"
CONDITIONS = ("A", "B", "C")


def load_cases(path: Path = DEFAULT_CASES) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases") if isinstance(payload, dict) else None
    if payload.get("schema_version") != "m1-dev-pilot-v1" or payload.get("split") != "development_validation" or not payload.get("frozen_before_execution"):
        raise ValueError("M1 pilot manifest must be frozen development/validation v1")
    if not isinstance(cases, list) or len(cases) != 15 or len({item.get("id") for item in cases}) != 15:
        raise ValueError("M1 pilot requires exactly 15 unique preselected cases")
    return cases


@contextmanager
def runtime(provider: str):
    prior = {key: os.environ.get(key) for key in ("IMPLEMENTATION_PROFILE", "PROVIDER")}
    os.environ["IMPLEMENTATION_PROFILE"] = "m1"
    os.environ["PROVIDER"] = provider
    try:
        yield
    finally:
        for key, value in prior.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _atomic_write_json(path: Path, payload: dict[str, object]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


async def run_pilot(
    provider: str = "ollama",
    output_dir: Path = ROOT / "reports" / "m1_pilot" / EXPERIMENT_ID,
    runs_dir: Path = ROOT / "runs" / "m1_pilot" / EXPERIMENT_ID,
    selected_case_ids: set[str] | None = None,
    repeats: int = 1,
    phase: str = "smoke",
    conditions: tuple[str, ...] = CONDITIONS,
    experiment_id: str = EXPERIMENT_ID,
    experiment_freeze_id: str | None = None,
) -> dict:
    """Run one serial phase and checkpoint every case-condition-repeat record."""

    if provider not in {"ollama", "fake"}:
        raise ValueError("provider must be ollama or fake")
    if repeats < 1:
        raise ValueError("repeats must be at least 1")
    if not conditions or any(condition not in CONDITIONS for condition in conditions):
        raise ValueError("conditions must be a non-empty subset of A, B, C")

    cases = load_cases()
    if selected_case_ids is not None:
        cases = [case for case in cases if case["id"] in selected_case_ids]
    if not cases:
        raise ValueError("pilot phase must select at least one case")

    store = prepare_store(ROOT / "data" / experiment_id)
    runs = RunStore(str(runs_dir))
    with runtime(provider):
        cfg = RuntimeConfig.from_env()
        identity = {
            "experiment_id": experiment_id,
            "manifest_sha256": hashlib.sha256(DEFAULT_CASES.read_bytes()).hexdigest(),
            "provider": provider,
            "model": cfg.local_model,
            "implementation_profile": cfg.implementation_profile,
            "config_hash": cfg.config_hash(),
            "source_snapshot_id": store.snapshot_id(),
            "experiment_freeze_id": experiment_freeze_id,
        }
        with single_writer_lock(output_dir):
            output_dir.mkdir(parents=True, exist_ok=True)
            ledger = PilotLedger(output_dir / "canonical_attempt_ledger.json", identity)
            pipeline = ResearchPipeline(store, runs)
            for case in cases:
                for condition in conditions:
                    for repeat in range(1, repeats + 1):
                        key = f"{case['id']}|{condition}|repeat-{repeat}"
                        if key in ledger.canonical_keys():
                            continue
                        try:
                            run = await pipeline.run(case["query"], condition, provider)
                        except Exception as exc:
                            run = {
                                "run_id": "", "status": "FAILED", "metrics": {},
                                "events": [{"stage": "runner_failed", "error_type": type(exc).__name__}],
                                "answer": "", "tasks": [], "task_results": [], "effective_config": {},
                            }
                        record = {
                            "key": key, "case_id": case["id"], "kind": case["kind"],
                            "condition": condition, "repeat": repeat, "phase": phase,
                            "status": run["status"], "run_id": run["run_id"],
                            "metrics": run["metrics"], "events": run["events"],
                            "answer": run["answer"], "tasks": run["tasks"],
                            "task_results": run["task_results"],
                            "effective_config": run["effective_config"],
                            "freeze_ids": {"experiment_freeze_id": experiment_freeze_id},
                        }
                        ledger.append(record)
                        _atomic_write_json(output_dir / f"{experiment_id}_{provider}.json", ledger.report())
                        print(f"{case['id']} {condition} repeat={repeat} {run['status']}", flush=True)
            report = ledger.report()
            path = output_dir / f"{experiment_id}_{provider}.json"
            _atomic_write_json(path, report)
    return {"report": report, "path": path}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", default="ollama", choices=["ollama", "fake"])
    parser.add_argument("--phase", choices=["smoke", "full", "recheck"], default="smoke")
    parser.add_argument("--experiment-id", default=EXPERIMENT_ID)
    parser.add_argument("--conditions", nargs="+", choices=CONDITIONS)
    parser.add_argument("--case-ids", nargs="+")
    parser.add_argument("--experiment-freeze-id")
    args = parser.parse_args()
    selected = set(args.case_ids) if args.case_ids else ({"M1-01", "M1-02", "M1-03"} if args.phase == "smoke" else None)
    repeats = 3 if args.phase == "full" else 1
    output_dir = ROOT / "reports" / "m1_pilot" / args.experiment_id
    runs_dir = ROOT / "runs" / "m1_pilot" / args.experiment_id
    print(asyncio.run(run_pilot(args.provider, output_dir, runs_dir, selected, repeats, args.phase, tuple(args.conditions or CONDITIONS), args.experiment_id, args.experiment_freeze_id))["path"])
