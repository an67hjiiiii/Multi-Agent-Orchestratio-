from __future__ import annotations

from pydantic import BaseModel, model_validator


class PlanningKnowledgeItem(BaseModel):
    id: str
    domain: str
    title: str
    content: str
    provenance: str


class PlanningRetrievalResult(BaseModel):
    request: str
    item_ids: list[str]
    scores: list[float] | None
    context: str


class TaskItem(BaseModel):
    task_id: str
    title: str
    objective: str
    expected_output: str
    domain: str
    role_profile: str
    depends_on: list[str]


class TaskPlan(BaseModel):
    """The exact JSON object emitted by the P-lite planner."""

    tasks: list[TaskItem]


def validate_task_dependencies(tasks: list[TaskItem]) -> None:
    task_ids = [task.task_id for task in tasks]
    if len(task_ids) != len(set(task_ids)):
        raise ValueError("Duplicate task IDs are not allowed")

    known_ids = set(task_ids)
    dependencies = {task.task_id: task.depends_on for task in tasks}
    for task in tasks:
        for dependency_id in task.depends_on:
            if dependency_id not in known_ids:
                raise ValueError(f"Unknown dependency ID: {dependency_id}")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visiting:
            raise ValueError("Task dependencies contain a cycle")
        if task_id in visited:
            return

        visiting.add(task_id)
        for dependency_id in dependencies[task_id]:
            visit(dependency_id)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in task_ids:
        visit(task_id)


class DecompositionResult(BaseModel):
    request: str
    tasks: list[TaskItem]
    planning_evidence_ids: list[str]
    status: str
    warnings: list[str]

    @model_validator(mode="after")
    def validate_dependencies(self) -> DecompositionResult:
        validate_task_dependencies(self.tasks)
        return self
