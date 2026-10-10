from dataclasses import asdict

from app.core.types import Concern, Obligation, Task, TaskPlan


def test_obligation_and_concern_are_distinct_serializable_contracts():
    obligation = Obligation(
        obligation_id="REQ-1",
        description="Preserve the requested error-response requirement.",
    )
    concern = Concern(
        concern_id="CONCERN-1",
        description="Check that the error response is actionable.",
        domain="api_architecture",
    )

    assert asdict(obligation) == {
        "obligation_id": "REQ-1",
        "description": "Preserve the requested error-response requirement.",
        "required": True,
    }
    assert asdict(concern) == {
        "concern_id": "CONCERN-1",
        "description": "Check that the error response is actionable.",
        "domain": "api_architecture",
    }


def test_task_plan_schema_keeps_obligations_concerns_and_dependencies():
    plan = TaskPlan(
        request="Review identity, permission, and persistence behavior.",
        obligations=[Obligation("REQ-1", "Verify user identity.")],
        concerns=[Concern("CONCERN-1", "Check authorization.", "security")],
        tasks=[
            Task(task_id="T1", goal="Review identity", domain="security"),
            Task(
                task_id="T2",
                goal="Review permission",
                domain="security",
                depends_on=["T1"],
            ),
        ],
    )

    payload = asdict(plan)
    assert payload["request"].startswith("Review identity")
    assert payload["obligations"][0]["obligation_id"] == "REQ-1"
    assert payload["concerns"][0]["concern_id"] == "CONCERN-1"
    assert payload["tasks"][1]["depends_on"] == ["T1"]
