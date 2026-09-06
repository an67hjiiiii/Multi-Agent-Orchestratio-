import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PILOT_PATH = ROOT / "datasets" / "planning" / "p_lite_pilot_cases.json"


def _load_pilot() -> dict:
    return json.loads(PILOT_PATH.read_text(encoding="utf-8"))


def _all_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _all_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _all_keys(child)


def test_p_lite_pilot_is_structural_only():
    pilot = _load_pilot()

    assert pilot["schema_version"] == "sprint3-p-lite-pilot-v1"
    assert pilot["scope"]["evidence_mode"] == "structural_only"
    assert pilot["scope"]["live_calibration"] is False
    assert pilot["scope"]["semantic_answer_scoring"] == "not_in_scope"

    forbidden_keys = {
        "answer",
        "correct_answer",
        "expected_answer",
        "final_answer",
        "gold_answer",
        "rubric",
    }
    assert not forbidden_keys.intersection(set(_all_keys(pilot)))


def test_p_lite_pilot_covers_the_five_required_case_shapes():
    pilot = _load_pilot()
    cases = pilot["cases"]

    assert len(cases) == 5
    assert {case["label"] for case in cases} == {
        "one_task",
        "chained",
        "partially_independent",
        "ambiguous",
        "weak_no_planning_evidence",
    }
    assert len({case["case_id"] for case in cases}) == len(cases)
    assert all(case["request"].strip() for case in cases)


def test_p_lite_case_graph_contracts_are_explicit():
    pilot = _load_pilot()
    by_label = {case["label"]: case for case in pilot["cases"]}

    assert by_label["one_task"]["expected_structure"]["task_count"] == {"exact": 1}
    assert by_label["chained"]["expected_structure"]["task_count"] == {"exact": 2}
    assert by_label["partially_independent"]["expected_structure"]["task_count"] == {"exact": 3}

    for label in ("ambiguous", "weak_no_planning_evidence"):
        expected = by_label[label]["expected_structure"]
        assert expected["task_count"]["min"] >= 1
        assert expected["task_count"]["max"] >= expected["task_count"]["min"]
        assert expected["dependency_graph"]["shape"] == "valid_acyclic_graph"

    assert by_label["one_task"]["expected_structure"]["dependency_graph"]["shape"] == "single_node"
    assert by_label["chained"]["expected_structure"]["dependency_graph"]["shape"] == "single_chain"
    assert (
        by_label["partially_independent"]["expected_structure"]["dependency_graph"]["shape"]
        == "chain_plus_isolated_node"
    )

    for case in pilot["cases"]:
        expected = case["expected_structure"]
        graph = expected["dependency_graph"]
        evidence = expected["planning_evidence_ids"]
        assert graph["acyclic"] is True
        assert evidence["unique"] is True
        assert 0 <= evidence["max_items"] <= pilot["collection_requirements"]["planning_evidence_ids"]["max_items"]


def test_p_lite_collection_requirements_preserve_failure_and_metric_boundaries():
    pilot = _load_pilot()
    requirements = pilot["collection_requirements"]

    assert requirements["terminal_statuses"] == [
        "COMPLETE",
        "PARTIAL",
        "NO_EVIDENCE",
        "FAILED",
    ]
    assert requirements["planning_evidence_ids"]["answer_evidence_is_separate"] is True
    assert requirements["latency"]["unit"] == "milliseconds"
    assert requirements["latency"]["unavailable_value"] is None
    assert requirements["llm_calls"]["decomposition_retry_limit"] == 1
    assert requirements["llm_calls"]["decomposition_call_upper_bound"] == 2
    assert requirements["dependency_validation"]["silent_dependency_drop"] is False
    assert requirements["task_coverage"]["pilot_value"] == "NOT_SCORED"
    assert requirements["task_coverage"]["numeric_values_when_unavailable"] is None
