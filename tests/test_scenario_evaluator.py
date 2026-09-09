from __future__ import annotations

import json

from app.evaluation.scenario_evaluator import (
    PENDING_HUMAN_REVIEW,
    build_case_gold_index,
    build_scenario_evaluation_row,
    evaluate_scenario_gold_after_inference,
)


def _benchmark() -> dict:
    return {
        "scenario_groups": [
            {
                "scenario_group_id": "M1F-S01",
                "scenario_gold_id": "M1F-G01",
                "variants": [{"case_id": "M1F-S01-V01"}],
            }
        ]
    }


def _gold() -> dict:
    return {
        "status": "PENDING_HUMAN_APPROVAL",
        "scenario_gold": [
            {
                "scenario_gold_id": "M1F-G01",
                "scenario_group_id": "M1F-S01",
                "expected_status": "COMPLETE",
                "expected_role": "Security Analyst",
                "expected_roles": ["Security Analyst"],
                "expected_domain": "security",
                "expected_domains": ["security"],
                "relevant_evidence_ids": ["e1"],
                "expected_answer_points": ["identity"],
                "expected_missing_information": "NONE",
                "dependency_expectation": "NOT_APPLICABLE",
                "normalization_expectation": "NOT_APPLICABLE",
                "overlap_expectation": "NOT_APPLICABLE",
                "reviewer_status": "PENDING_HUMAN_APPROVAL",
            }
        ],
    }


def _attempt() -> dict:
    return {
        "attempt_id": "a1",
        "case_id": "M1F-S01-V01",
        "condition": "C",
        "status": "COMPLETE",
        "tasks": [{"task_id": "T1", "depends_on": []}],
        "task_results": [
            {
                "task_id": "T1",
                "missing_information": ["m1"],
                "status_reason": "bounded_answer",
            }
        ],
        "metrics": {
            "citations_emitted": 1,
            "citations_valid": 1,
            "citation_locator_validity": 1.0,
        },
        "events": [
            {
                "stage": "run_started",
                "flags": {"P": True, "N": True, "O": True},
            },
            {"stage": "planning_retrieval", "selected": ["p1"]},
            {"stage": "decomposition", "tasks": []},
            {"stage": "normalization", "removed": 0},
            {
                "stage": "task_retrieval",
                "candidates": ["e1", "e2"],
                "selected": ["e1"],
                "dropped": [{"chunk_id": "e2"}],
                "shared_evidence_ids": ["e1"],
            },
            {"stage": "overlap_summary", "o_enabled": True},
        ],
    }


def test_index_and_structural_gold_join_do_not_score_semantics():
    index = build_case_gold_index(_benchmark(), _gold())
    row = build_scenario_evaluation_row(_attempt(), index["M1F-S01-V01"])

    assert row["scenario_group_id"] == "M1F-S01"
    assert row["automatic"]["candidate_evidence_recall_at_k"] == 1.0
    assert row["automatic"]["selected_evidence_recall"] == 1.0
    assert row["observed"]["dropped_evidence_ids"] == ["e2"]
    assert row["observed"]["dropped_evidence"] == [{"chunk_id": "e2"}]
    assert row["observed"]["planning_evidence_ids"] == ["p1"]
    assert row["observed"]["missing_information"] == ["m1"]
    assert row["observed"]["status_reasons"] == [
        {"task_id": "T1", "status_reason": "bounded_answer"}
    ]
    assert row["automatic"]["condition_trace"]["flags_match_condition"] is True
    assert row["observed"]["dependency_graph_valid"] is True
    assert row["human_evaluation"]["answer_quality"] == PENDING_HUMAN_REVIEW
    assert row["human_evaluation"]["faithfulness"] == PENDING_HUMAN_REVIEW
    assert row["gold_reference"]["expected_role"] == "Security Analyst"
    assert row["gold_reference"]["expected_domain"] == "security"


def test_independent_annotations_enable_existing_task_coverage_only():
    row = build_scenario_evaluation_row(
        _attempt(),
        _gold()["scenario_gold"][0],
        annotations={
            "M1F-S01-V01": {
                "gold_obligation_ids": ["R1"],
                "task_matches": {"T1": ["R1"]},
                "annotations_complete": True,
            }
        },
    )
    assert row["human_evaluation"]["task_coverage"]["value"] == 1.0
    assert row["human_evaluation"]["answer_points"] == PENDING_HUMAN_REVIEW


def test_post_inference_wrapper_loads_gold_after_terminal_report(tmp_path):
    report = tmp_path / "report.json"
    report.write_text(
        json.dumps(
            {
                "report_schema": "final-six-condition-report-v1",
                "inference_complete": True,
                "rows": [_attempt()],
            }
        ),
        encoding="utf-8",
    )
    events: list[str] = []

    def benchmark_loader():
        events.append("benchmark")
        return _benchmark()

    def gold_loader():
        events.append("gold")
        return _gold()

    result = evaluate_scenario_gold_after_inference(report, benchmark_loader, gold_loader)
    assert events == ["benchmark", "gold"]
    assert result["gold_loaded_after_inference"] is True
    assert result["rows"][0]["scenario_group_id"] == "M1F-S01"
