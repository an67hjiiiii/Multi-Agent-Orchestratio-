"""Stage-owned research contracts and compatibility adapters.

The planner and executor represent different stages of the same task. The
adapter below keeps both shapes explicit and preserves every planning field at
the execution boundary.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from app.core.types import Status, Task, TaskResult
from app.research.task_schema import DecompositionResult, TaskItem


# TaskResult is the established worker wire shape. This name documents its
# owner without changing construction, isinstance checks, or JSON output.
WorkerResult = TaskResult


def _values(item: TaskItem | Mapping[str, Any] | Task) -> dict[str, Any]:
    if isinstance(item, Task):
        return asdict(item)
    model_dump = getattr(item, "model_dump", None)
    if callable(model_dump):
        return dict(model_dump())
    if isinstance(item, Mapping):
        return dict(item)
    raise TypeError("planning task must be a TaskItem, mapping, or Task")


def planning_task_to_runtime(item: TaskItem | Mapping[str, Any] | Task) -> Task:
    """Adapt a planning task without dropping planning-only metadata."""

    if isinstance(item, Task):
        return item
    values = _values(item)
    return Task(
        task_id=str(values["task_id"]),
        goal=str(values["objective"]),
        domain=str(values["domain"]),
        depends_on=list(values.get("depends_on", [])),
        title=str(values.get("title", "")),
        expected_output=str(values.get("expected_output", "")),
        role_profile=str(values.get("role_profile", "")),
        covers_obligations=list(values.get("covers_obligations", [])),
    )


@dataclass(frozen=True)
class FinalResult:
    """Typed view of the existing final answer boundary."""

    status: Status | str
    answer: str
    citations: list[str] = field(default_factory=list)
    missing_information: list[str] = field(default_factory=list)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "FinalResult":
        return cls(
            status=str(value.get("status") or "PARTIAL"),
            answer=str(value.get("answer") or ""),
            citations=[str(item) for item in value.get("citations", []) or []],
            missing_information=[
                str(item) for item in value.get("missing_information", []) or []
            ],
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ValidationResult:
    """Typed view of validation data already emitted by decomposition."""

    status: str
    missing_obligations: list[str] = field(default_factory=list)
    missing_concerns: list[str] = field(default_factory=list)
    misrouted_concerns: list[str] = field(default_factory=list)
    dependency_issues: list[str] = field(default_factory=list)
    reason: str | None = None

    @classmethod
    def from_decomposition(cls, value: DecompositionResult) -> "ValidationResult":
        return cls(
            status=str(value.status),
            missing_obligations=list(value.missing_obligations),
            missing_concerns=list(getattr(value, "missing_concerns", [])),
            misrouted_concerns=list(getattr(value, "misrouted_concerns", [])),
            dependency_issues=list(getattr(value, "dependency_issues", [])),
            reason=value.coverage_validation_reason,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


__all__ = [
    "FinalResult",
    "ValidationResult",
    "WorkerResult",
    "planning_task_to_runtime",
]
