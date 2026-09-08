from pathlib import Path

from scripts.validate_m1_final_dataset import validate


def test_m1_final_dataset_static_readiness_passes():
    result = validate(Path(__file__).parents[1])
    assert result["decision"] == "PASS", result["errors"]
    assert result["scenario_group_count"] == 30
    assert result["frozen_request_count"] == 120
    assert result["scenario_gold_count"] == 30
    assert result["approval_status"] == "PENDING_HUMAN_APPROVAL"
    assert result["runtime_isolation"]["existing_guard_decision"] == "PASS"
    assert result["runtime_isolation"]["marker_hits"] == []
