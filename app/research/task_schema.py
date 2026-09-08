from __future__ import annotations

from typing import Final, Literal, TypeAlias

from pydantic import BaseModel, Field, model_validator


CANONICAL_TASK_DOMAINS: Final[frozenset[str]] = frozenset(
    {"security", "database", "api_architecture"}
)
CanonicalTaskDomain: TypeAlias = Literal[
    "security",
    "database",
    "api_architecture",
]


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


class RequiredObligation(BaseModel):
    """One stable obligation derived from text explicitly present in a request."""

    obligation_id: str
    canonical_kind: CanonicalTaskDomain | None = None
    source_anchor: str


class TaskItem(BaseModel):
    task_id: str
    title: str
    objective: str
    expected_output: str
    domain: CanonicalTaskDomain
    role_profile: str
    depends_on: list[str]
    covers_obligations: list[str] = Field(default_factory=list)


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
    required_obligations: list[RequiredObligation] = Field(default_factory=list)
    covered_obligations: list[str] = Field(default_factory=list)
    missing_obligations: list[str] = Field(default_factory=list)
    repair_attempted: bool = False
    coverage_validation_reason: str | None = None

    @model_validator(mode="after")
    def validate_dependencies(self) -> DecompositionResult:
        validate_task_dependencies(self.tasks)
        return self
