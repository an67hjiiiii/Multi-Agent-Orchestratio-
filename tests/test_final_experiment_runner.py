from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from app.evaluation.final_experiment import (
    APPROVED,
    FINAL_CONDITIONS,
    FinalAttemptLedger,
    LaunchBlockedError,
    evaluate_after_inference,
    run_final_experiment,
)


def _write_cases(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "final-experiment-cases-v1",
                "cases": [{"id": "F-01", "kind": "fact", "query": "What is the local fact?"}],
            }
        ),
        encoding="utf-8",
    )


class _FakePipeline:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    async def run(self, query: str, condition: str, provider: str) -> dict:
        self.calls.append((query, condition, provider))
        return {
            "status": "COMPLETE",
            "run_id": f"run-{len(self.calls)}",
            "answer": "Fake answer",
            "metrics": {"llm_calls": 1},
            "events": [{"stage": "run_finished", "status": "COMPLETE"}],
            "tasks": [],
            "task_results": [],
        }


def test_pending_approval_blocks_even_before_cases_are_loaded(tmp_path):
    with pytest.raises(LaunchBlockedError, match="launch blocked"):
        asyncio.run(
            run_final_experiment(
                cases_path=tmp_path / "does-not-exist.json",
                output_dir=tmp_path / "reports",
                runs_dir=tmp_path / "runs",
            )
        )


def test_canonical_final_manifest_flattens_request_variants_only():
    manifest = Path(__file__).parents[1] / "datasets" / "final" / "final_benchmark_v1.json"
    from app.evaluation.final_experiment import load_cases

    cases = load_cases(manifest)
    assert len(cases) == 120
    assert cases[0].case_id == "M1F-S01-V01"
    assert cases[0].query.startswith("Trace the security handoff")
    assert cases[-1].case_id == "M1F-S30-V04"


def test_dry_run_reports_explicit_pending_approval_block_without_pipeline(tmp_path):
    result = asyncio.run(
        run_final_experiment(
            cases_path=tmp_path / "does-not-exist.json",
            output_dir=tmp_path / "reports",
            runs_dir=tmp_path / "runs",
            dry_run=True,
        )
    )
    assert result["plan"]["launch_status"] == "BLOCKED"
    assert "PENDING_HUMAN_APPROVAL" in result["plan"]["block_reason"]
    assert result["report"] is None


def test_serial_six_conditions_checkpoint_resume_and_stable_ids(tmp_path):
    cases = tmp_path / "cases.json"
    _write_cases(cases)
    pipeline = _FakePipeline()
    first = asyncio.run(
        run_final_experiment(
            cases_path=cases,
            output_dir=tmp_path / "reports",
            runs_dir=tmp_path / "runs",
            provider="fake",
            dataset_status=APPROVED,
            gold_status=APPROVED,
            pipeline_factory=lambda _: pipeline,
        )
    )
    assert [call[1] for call in pipeline.calls] == list(FINAL_CONDITIONS)
    assert first["report"]["run_count"] == 6
    rows = first["report"]["rows"]
    assert len({row["attempt_id"] for row in rows}) == 6
    assert all(row["effective_config"]["config_hash"] for row in rows)

    resumed_pipeline = _FakePipeline()
    resumed = asyncio.run(
        run_final_experiment(
            cases_path=cases,
            output_dir=tmp_path / "reports",
            runs_dir=tmp_path / "runs",
            provider="fake",
            dataset_status=APPROVED,
            gold_status=APPROVED,
            pipeline_factory=lambda _: resumed_pipeline,
        )
    )
    assert resumed_pipeline.calls == []
    assert resumed["report"]["run_count"] == 6
    assert resumed["report"]["attempt_count"] == 6


def test_failure_is_terminal_and_append_only(tmp_path):
    ledger = FinalAttemptLedger(tmp_path / "ledger.jsonl", {"config_hash": "frozen"})
    ledger.append_terminal({"key": "F-01|A|repeat-1", "status": "FAILED", "attempt_id": "a1"})
    assert ledger.canonical_keys() == {"F-01|A|repeat-1"}
    assert len((tmp_path / "ledger.jsonl").read_text(encoding="utf-8").splitlines()) == 1
    with pytest.raises(ValueError, match="terminal statuses"):
        ledger.append_terminal({"key": "F-01|B|repeat-1", "status": "RUNNING"})


def test_evaluator_calls_gold_loader_only_after_terminal_report(tmp_path):
    report = tmp_path / "report.json"
    report.write_text(
        json.dumps(
            {
                "report_schema": "final-six-condition-report-v1",
                "inference_complete": True,
                "rows": [{
                    "attempt_id": "a1",
                    "case_id": "F-01",
                    "condition": "A",
                    "status": "COMPLETE",
                }],
            }
        ),
        encoding="utf-8",
    )
    events: list[str] = []

    def load_gold():
        events.append("gold")
        return {"F-01": "human-owned gold"}

    result = evaluate_after_inference(report, load_gold)
    assert events == ["gold"]
    assert result["gold_loaded_after_inference"] is True
    assert result["human_grading"] == "PENDING"
