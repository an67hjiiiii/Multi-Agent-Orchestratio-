from __future__ import annotations

import asyncio
import csv
import json
import os
from pathlib import Path

import pytest

from app.storage.source_store import SourceStore
from scripts.run_m0_calibration import (
    EXPECTED_CASE_IDS,
    REPORT_FIELDS,
    build_case_row,
    load_cases,
    run_calibration,
    validate_cases,
)


def test_m0_manifest_is_the_locked_12_case_shape():
    manifest_path = Path(__file__).parents[1] / "datasets" / "calibration" / "m0_cases.json"
    original = json.loads(manifest_path.read_text(encoding="utf-8"))

    cases = load_cases(manifest_path)

    assert [case["id"] for case in cases] == list(EXPECTED_CASE_IDS)
    assert sum(case["expected_evidence"] == "present" for case in cases) == 9
    assert sum(case["expected_evidence"] == "missing" for case in cases) == 3
    assert cases == original


def test_manifest_validation_rejects_missing_case_without_rewriting_gold():
    cases = load_cases()
    malformed = cases[:-1]

    with pytest.raises(ValueError, match="exactly 12 cases"):
        validate_cases(malformed)

    assert len(cases) == 12
    assert cases[-1]["id"] == "M0-12"


def test_fake_runner_writes_stable_rows_and_report_metadata(tmp_path, monkeypatch):
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "sentinel-profile")
    monkeypatch.setenv("PROVIDER", "sentinel-provider")
    result = asyncio.run(
        run_calibration(
            provider="fake",
            data_dir=tmp_path / "data",
            runs_dir=tmp_path / "runs",
            output_dir=tmp_path / "reports",
            stamp="fixed",
        )
    )

    report = result["report"]
    rows = report["rows"]
    summary = report["summary"]
    assert report["report_schema"] == "m0-calibration-v2"
    assert report["condition"] == "A"
    assert report["implementation_profile"] == "m0"
    assert report["provider"] == "fake"
    assert report["dataset"]["case_ids"] == list(EXPECTED_CASE_IDS)
    assert len(report["dataset"]["sha256"]) == 64
    assert [row["case_id"] for row in rows] == list(EXPECTED_CASE_IDS)
    assert summary["case_count"] == 12
    assert summary["automated_pass_count"] == 12
    assert summary["automated_pass_rate"] == 1.0
    assert summary["status_counts"] == {"COMPLETE": 9, "NO_EVIDENCE": 3}
    assert summary["manual_correctness"] == {"UNSCORED": 12}
    assert summary["manual_faithfulness"] == {"UNSCORED": 12}
    assert report["evidence_boundary"].endswith("semantic correctness or faithfulness.")
    assert os.environ["IMPLEMENTATION_PROFILE"] == "sentinel-profile"
    assert os.environ["PROVIDER"] == "sentinel-provider"

    with result["csv_path"].open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == list(REPORT_FIELDS)
        csv_rows = list(reader)
    assert [row["case_id"] for row in csv_rows] == list(EXPECTED_CASE_IDS)
    assert result["json_path"].name == "m0_calibration_fake_fixed.json"
    assert result["csv_path"].name == "m0_calibration_fake_fixed.csv"


def test_present_case_with_missing_locator_telemetry_does_not_pass(tmp_path):
    store = SourceStore(str(tmp_path / "data"))
    imported = store.import_text("source.md", "The source contains the requested evidence.")
    chunk_id = store.source(imported["source_id"])["chunks"][0]["chunk_id"]
    case = {
        "id": "M0-01",
        "query": "What evidence is present?",
        "expected_source": "source.md",
        "expected_evidence": "present",
    }
    run = {
        "condition": "A",
        "implementation_profile": "m0",
        "status": "COMPLETE",
        "answer": "answer",
        "model": "test-model",
        "task_results": [{"citations": [chunk_id], "invalid_citations": []}],
        "metrics": {"citation_locator_validity": None},
    }

    row = build_case_row(case, run, store)

    assert row["citation_count"] == 1
    assert row["locator_valid"] is False
    assert row["automated_pass"] is False
