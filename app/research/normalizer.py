"""Conservative M1 rules-only task normalization."""
from __future__ import annotations

from dataclasses import asdict
from app.core.graph import validate_tasks
from app.core.types import Task


def _clean(value: str) -> str:
    return " ".join(value.casefold().split())


def _signature(task: Task) -> tuple[object, ...]:
    """Only exact canonical duplicates merge; shared domain never suffices."""
    return (
        _clean(task.domain), _clean(task.object or task.goal), _clean(task.action),
        _clean(task.deliverable or task.goal),
        tuple(sorted(_clean(value) for value in task.requirement_ids)),
        tuple(sorted(_clean(value) for value in task.constraints)),
    )


def normalize_tasks_with_trace(tasks: list[Task]) -> tuple[list[Task], list[dict[str, object]]]:
    validate_tasks(tasks)
    kept: list[Task] = []
    replacement: dict[str, str] = {}
    merged_dependencies: dict[str, list[str]] = {}
    trace: list[dict[str, object]] = []
    signatures: dict[tuple[object, ...], Task] = {}
    for task in tasks:
        existing = signatures.get(_signature(task))
        if existing is None:
            kept.append(task); signatures[_signature(task)] = task; replacement[task.task_id] = task.task_id
            merged_dependencies[task.task_id] = list(task.depends_on)
            trace.append({"decision": "KEEP", "task_id": task.task_id, "reason": "distinct_or_first"})
        else:
            replacement[task.task_id] = existing.task_id
            merged_dependencies[existing.task_id].extend(task.depends_on)
            trace.append({"decision": "MERGE", "task_id": task.task_id, "into_task_id": existing.task_id, "reason": "exact_canonical_duplicate"})
    proposed = []
    for task in kept:
        values = asdict(task)
        values["depends_on"] = list(dict.fromkeys(
            replacement[item] for item in merged_dependencies[task.task_id]
        ))
        proposed.append(Task(**values))
    try:
        validate_tasks(proposed)
    except ValueError as exc:
        trace.append({"decision": "ROLLBACK", "reason": f"dependency_remap_invalid:{exc}"})
        return list(tasks), trace
    return proposed, trace


def normalize_tasks(tasks: list[Task]) -> tuple[list[Task], int]:
    normalized, trace = normalize_tasks_with_trace(tasks)
    return normalized, len(tasks) - len(normalized)
