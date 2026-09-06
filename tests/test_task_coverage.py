import pytest

from app.evaluation.task_coverage import (
    DEFINED,
    PARTIAL,
    UNDEFINED,
    calculate_task_coverage,
)


def test_complete_annotation_counts_each_gold_obligation_once():
    result = calculate_task_coverage(
        ["R2", "R1", "R1"],
        {
            "T2": ["R2", "R1"],
            "T1": ["R1"],
        },
    )

    assert result.status == DEFINED
    assert result.value == 1.0
    assert result.covered_count == 2
    assert result.total_obligations == 2
    assert result.covered_obligation_ids == ("R1", "R2")
    assert result.uncovered_obligation_ids == ()
    assert result.unassessed_obligation_ids == ()
    assert result.is_lower_bound is False


def test_empty_task_plan_is_defined_as_zero_when_review_is_complete():
    result = calculate_task_coverage(["R1", "R2"], {})

    assert result.status == DEFINED
    assert result.value == 0.0
    assert result.covered_count == 0
    assert result.uncovered_obligation_ids == ("R1", "R2")


def test_incomplete_annotation_is_partial_and_exposes_lower_bound():
    result = calculate_task_coverage(
        ["R1", "R2"],
        {"T1": ["R1"], "T2": None},
        annotations_complete=False,
    )

    assert result.status == PARTIAL
    assert result.value == pytest.approx(0.5)
    assert result.is_lower_bound is True
    assert result.covered_obligation_ids == ("R1",)
    assert result.uncovered_obligation_ids == ()
    assert result.unassessed_obligation_ids == ("R2",)
    assert "lower bound" in result.reason


@pytest.mark.parametrize(
    ("gold_ids", "matches", "reason"),
    [
        (None, {}, "gold obligations are unavailable"),
        ([], {}, "the case has no gold obligations"),
        (["R1"], None, "independent task-match annotations are unavailable"),
    ],
)
def test_missing_measurement_inputs_are_undefined(gold_ids, matches, reason):
    result = calculate_task_coverage(gold_ids, matches)

    assert result.status == UNDEFINED
    assert result.value is None
    assert result.reason == reason


def test_unknown_match_is_rejected_instead_of_changing_the_denominator():
    with pytest.raises(ValueError, match="unknown gold obligations: R2"):
        calculate_task_coverage(["R1"], {"T1": ["R2"]})


def test_serialized_result_preserves_partial_state():
    result = calculate_task_coverage(
        ["R1", "R2"],
        {"T1": ["R1"]},
        annotations_complete=False,
    )

    assert result.to_dict() == {
        "metric": "task_coverage",
        "status": PARTIAL,
        "value": 0.5,
        "covered_obligations": 1,
        "total_obligations": 2,
        "covered_obligation_ids": ["R1"],
        "uncovered_obligation_ids": [],
        "unassessed_obligation_ids": ["R2"],
        "annotated_task_count": 1,
        "annotations_complete": False,
        "is_lower_bound": True,
        "reason": "task-match annotation is incomplete; value is a lower bound",
    }
