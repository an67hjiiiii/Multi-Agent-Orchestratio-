"""Prepare validated planning output for runtime execution.

Planning remains responsible for TaskItem semantics and semantic dependencies.
This module only adapts those tasks, optionally applies N, and asks the stable
graph primitive for an executable order.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.graph import topological_order
from app.core.types import Task
from app.orchestration.normalization import normalize_tasks_with_trace
from app.research.contracts import planning_task_to_runtime


@dataclass(frozen=True)
class RuntimeTaskPreparation:
    """Validated runtime tasks and their executable order."""

    tasks: list[Task]
    ordered_tasks: list[Task]
    normalization_trace: list[dict[str, object]]
    duplicate_tasks_removed: int


def runtime_tasks_from_plan(decomposition: object) -> list[Task]:
    """Adapt planning output without reinterpreting semantic dependencies."""

    raw_tasks = getattr(decomposition, "tasks", decomposition)
    if not isinstance(raw_tasks, list):
        raise TypeError("decomposition must provide a task list")

    tasks: list[Task] = []
    for item in raw_tasks:
        if isinstance(item, Task):
            tasks.append(item)
            continue
        model_dump = getattr(item, "model_dump", None)
        if not callable(model_dump):
            raise TypeError("decomposition task must use the canonical task schema")
        tasks.append(planning_task_to_runtime(item))
    return tasks


def prepare_runtime_tasks(
    tasks: list[Task],
    *,
    normalize: bool,
) -> RuntimeTaskPreparation:
    """Apply runtime-only preparation after planning validation succeeds."""

    normalization_trace: list[dict[str, object]] = []
    duplicate_tasks_removed = 0
    if normalize:
        task_count_before_normalization = len(tasks)
        tasks, normalization_trace = normalize_tasks_with_trace(tasks)
        duplicate_tasks_removed = task_count_before_normalization - len(tasks)

    return RuntimeTaskPreparation(
        tasks=tasks,
        ordered_tasks=topological_order(tasks),
        normalization_trace=normalization_trace,
        duplicate_tasks_removed=duplicate_tasks_removed,
    )


__all__ = [
    "RuntimeTaskPreparation",
    "prepare_runtime_tasks",
    "runtime_tasks_from_plan",
]
