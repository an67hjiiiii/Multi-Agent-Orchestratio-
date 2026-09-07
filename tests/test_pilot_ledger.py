import json

import pytest

from app.evaluation.pilot_ledger import PilotLedger, PilotLockedError, canonical_metric_snapshot, propose_raw_mapping, single_writer_lock


def _record(key: str, status: str = "COMPLETE") -> dict:
    return {"key": key, "status": status, "run_id": "raw_" + key, "metrics": {}, "events": []}


def test_second_writer_is_refused_and_first_releases_lock(tmp_path):
    with single_writer_lock(tmp_path):
        with pytest.raises(PilotLockedError):
            with single_writer_lock(tmp_path):
                pass
    with single_writer_lock(tmp_path):
        pass


def test_checkpoint_resume_skips_canonical_key_and_retains_terminal_failure(tmp_path):
    identity = {"manifest_sha256": "frozen", "provider": "fake", "model": "qwen3:4b"}
    first = PilotLedger(tmp_path / "ledger.json", identity)
    first.append(_record("M1-01|A"))
    first.append(_record("M1-01|B", "FAILED"))
    resumed = PilotLedger(tmp_path / "ledger.json", identity)
    assert resumed.canonical_keys() == {"M1-01|A", "M1-01|B"}
    assert resumed.report()["run_count"] == 2
    assert resumed.report()["rows"][1]["status"] == "FAILED"
    assert resumed.report() == PilotLedger(tmp_path / "ledger.json", identity).report()


def test_duplicate_is_preserved_as_raw_evidence_but_not_canonical_report_row(tmp_path):
    ledger = PilotLedger(tmp_path / "ledger.json", {"manifest_sha256": "frozen"})
    ledger.append(_record("M1-01|A", "PARTIAL"))
    ledger.append(_record("M1-01|A", "COMPLETE"))
    data = json.loads((tmp_path / "ledger.json").read_text(encoding="utf-8"))
    assert [item["classification"] for item in data["attempts"]] == ["canonical_attempt", "duplicate_attempt"]
    assert ledger.report()["run_count"] == 1


def test_raw_mapping_is_proposal_only_and_never_promotes_historical_runs():
    proposal = propose_raw_mapping([
        {"run_id": "r1", "created_at": "1", "query": "Q", "condition": "A"},
        {"run_id": "r2", "created_at": "2", "query": "Q", "condition": "A"},
    ])
    assert proposal[0]["proposed_classification"] == "raw_attempt_requires_owner_rule"
    assert proposal[1]["proposed_classification"] == "duplicate_attempt"


def test_metric_snapshot_is_condition_aware_and_preserves_missing_data():
    events = [
        {"stage": "normalization", "removed": 1, "tasks": [{"task_id": "T1"}]},
        {"stage": "task_retrieval", "selected": ["c1", "c2"], "shared_evidence_ids": ["c1"]},
    ]
    metrics = {"llm_calls": 2, "input_tokens": 4, "output_tokens": 5, "total_tokens": 9}
    c_snapshot = canonical_metric_snapshot(status="COMPLETE", condition="C", metrics=metrics, events=events)
    a_snapshot = canonical_metric_snapshot(status="COMPLETE", condition="A", metrics=metrics, events=events)
    assert c_snapshot["duplicate_task_rate"] == 0.5
    assert c_snapshot["overlap_reuse_ratio"] == 0.5
    assert c_snapshot["retry_count"] == "NOT_RECORDED"
    assert a_snapshot["duplicate_tasks_removed"] is None
    assert a_snapshot["overlap_reuse_ratio"] is None
