import pytest
from pydantic import ValidationError

from app.research.task_schema import (
    CANONICAL_TASK_DOMAINS,
    DecompositionResult,
    PlanningKnowledgeItem,
    PlanningRetrievalResult,
    TaskItem,
    validate_task_dependencies,
)


def make_task(task_id: str, depends_on: list[str] | None = None) -> TaskItem:
    return TaskItem(
        task_id=task_id,
        title=f"Task {task_id}",
        objective=f"Objective {task_id}",
        expected_output=f"Output {task_id}",
        domain="api_architecture",
        role_profile="API analyst",
        depends_on=depends_on or [],
    )


def test_locked_models_store_contract_fields() -> None:
    item = PlanningKnowledgeItem(
        id="p1",
        domain="api_architecture",
        title="API planning",
        content="Plan the API review.",
        provenance="planning.md#1",
    )
    retrieval = PlanningRetrievalResult(
        request="Review the API",
        item_ids=[item.id],
        scores=[0.9],
        context=item.content,
    )
    result = DecompositionResult(
        request=retrieval.request,
        tasks=[make_task("T1")],
        planning_evidence_ids=retrieval.item_ids,
        status="SUCCEEDED",
        warnings=[],
    )

    assert result.tasks[0].task_id == "T1"
    assert retrieval.scores == [0.9]


def test_duplicate_task_ids_are_rejected() -> None:
    tasks = [make_task("T1"), make_task("T1")]

    with pytest.raises(ValueError, match="Duplicate task IDs"):
        validate_task_dependencies(tasks)
    with pytest.raises(ValidationError, match="Duplicate task IDs"):
        DecompositionResult(
            request="request",
            tasks=tasks,
            planning_evidence_ids=[],
            status="FAILED",
            warnings=[],
        )


def test_unknown_dependency_ids_are_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown dependency ID: T2"):
        validate_task_dependencies([make_task("T1", ["T2"])])


def test_dependency_cycles_are_rejected() -> None:
    tasks = [make_task("T1", ["T2"]), make_task("T2", ["T1"])]

    with pytest.raises(ValueError, match="cycle"):
        validate_task_dependencies(tasks)


@pytest.mark.parametrize("domain", ["Security", "Database Management", "general"])
def test_noncanonical_task_domains_are_rejected(domain: str) -> None:
    assert CANONICAL_TASK_DOMAINS == frozenset(
        {"security", "database", "api_architecture"}
    )

    with pytest.raises(ValidationError, match="domain"):
        TaskItem(
            task_id="T1",
            title="Review",
            objective="Review the request.",
            expected_output="Findings.",
            domain=domain,
            role_profile="reviewer",
            depends_on=[],
        )
