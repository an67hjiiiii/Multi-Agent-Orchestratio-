from app.core.types import Task
from app.orchestration.normalization import normalize_tasks_with_trace
from app.orchestration.routing import worker_profile
from app.orchestration.task_preparation import (
    prepare_runtime_tasks,
    runtime_tasks_from_plan,
)
from app.research.task_schema import DecompositionResult, TaskItem


def test_runtime_preparation_preserves_planning_fields_and_semantic_dependencies():
    plan = DecompositionResult(
        request="Review identity before permissions.",
        tasks=[
            TaskItem(
                task_id="T1",
                title="Review identity",
                objective="Assess authentication",
                expected_output="Authentication findings",
                domain="security",
                role_profile="Security Analyst",
                depends_on=[],
                covers_obligations=["O1"],
            ),
            TaskItem(
                task_id="T2",
                title="Review permissions",
                objective="Assess authorization",
                expected_output="Authorization findings",
                domain="security",
                role_profile="Security Analyst",
                depends_on=["T1"],
                covers_obligations=["O2"],
            ),
        ],
        planning_evidence_ids=["P1"],
        status="COMPLETE",
        warnings=[],
    )

    runtime_tasks = runtime_tasks_from_plan(plan)
    prepared = prepare_runtime_tasks(runtime_tasks, normalize=False)

    assert [(task.task_id, task.goal, task.title) for task in prepared.tasks] == [
        ("T1", "Assess authentication", "Review identity"),
        ("T2", "Assess authorization", "Review permissions"),
    ]
    assert prepared.tasks[1].depends_on == ["T1"]
    assert prepared.tasks[1].expected_output == "Authorization findings"
    assert prepared.tasks[1].role_profile == "Security Analyst"
    assert prepared.tasks[1].covers_obligations == ["O2"]
    assert [task.task_id for task in prepared.ordered_tasks] == ["T1", "T2"]
    assert prepared.normalization_trace == []
    assert prepared.duplicate_tasks_removed == 0


def test_orchestration_keeps_existing_normalization_and_worker_routing_behavior():
    tasks = [
        Task("T1", "Review authentication", "security"),
        Task("T2", "Review authentication", "security"),
        Task("T3", "Review authorization", "security", depends_on=["T2"]),
    ]

    normalized, trace = normalize_tasks_with_trace(tasks)

    assert [task.task_id for task in normalized] == ["T1", "T3"]
    assert normalized[1].depends_on == ["T1"]
    assert any(item["decision"] == "MERGE" for item in trace)
    assert worker_profile("security")["name"] == "Security Analyst"
