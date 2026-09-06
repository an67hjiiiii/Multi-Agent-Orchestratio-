from __future__ import annotations

import inspect
import json
import re
from dataclasses import dataclass, field
from typing import Any

from app.core.types import RunMetrics


try:
    # The schema track is integrated separately; use its canonical types when
    # it is available while keeping this focused commit independently runnable.
    from app.research.task_schema import DecompositionResult, TaskItem
except ModuleNotFoundError as exc:
    if exc.name != "app.research.task_schema":
        raise

    @dataclass
    class TaskItem:
        task_id: str
        title: str
        objective: str
        expected_output: str
        domain: str
        role_profile: str
        depends_on: list[str] = field(default_factory=list)

    @dataclass
    class DecompositionResult:
        request: str
        tasks: list[TaskItem] = field(default_factory=list)
        planning_evidence_ids: list[str] = field(default_factory=list)
        status: str = "FAILED"
        warnings: list[str] = field(default_factory=list)


_PLANNING_ID_PATTERN = re.compile(r"\[([A-Za-z0-9_.:/-]+)\]")
_REQUIRED_TASK_FIELDS = (
    "task_id",
    "title",
    "objective",
    "expected_output",
    "domain",
    "role_profile",
)
_TASK_SCHEMA = (
    '{"tasks":[{"task_id":"T1","title":"short task title",'
    '"objective":"specific objective",'
    '"expected_output":"expected structured output",'
    '"domain":"declared domain",'
    '"role_profile":"declared role profile",'
    '"depends_on":[]}]}'
)


class _DecompositionOutputError(ValueError):
    """Raised when a model response cannot satisfy the P-lite contract."""


def _extract_planning_evidence_ids(planning_context: str) -> list[str]:
    """Preserve only evidence identifiers present in the bounded context."""

    return list(dict.fromkeys(_PLANNING_ID_PATTERN.findall(planning_context)))


def _extract_json(text: object) -> dict[str, Any]:
    if not isinstance(text, str) or not text.strip():
        raise _DecompositionOutputError("planner response was empty")

    cleaned = text.strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        if start < 0:
            raise _DecompositionOutputError("planner response did not contain a JSON object")
        try:
            parsed, _ = json.JSONDecoder().raw_decode(cleaned[start:])
        except json.JSONDecodeError as exc:
            raise _DecompositionOutputError("planner response contained invalid JSON") from exc

    if not isinstance(parsed, dict):
        raise _DecompositionOutputError("planner response must be a JSON object")
    return parsed


def _required_text(raw: dict[str, Any], field_name: str, task_index: int) -> str:
    value = raw.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise _DecompositionOutputError(
            f"task {task_index} field {field_name} must be a non-empty string"
        )
    return value.strip()


def _parse_tasks(parsed: dict[str, Any]) -> list[TaskItem]:
    raw_tasks = parsed.get("tasks")
    if not isinstance(raw_tasks, list) or not raw_tasks:
        raise _DecompositionOutputError("planner response must contain a non-empty tasks list")

    tasks: list[TaskItem] = []
    for index, raw in enumerate(raw_tasks, start=1):
        if not isinstance(raw, dict):
            raise _DecompositionOutputError(f"task {index} must be a JSON object")

        values = {
            field_name: _required_text(raw, field_name, index)
            for field_name in _REQUIRED_TASK_FIELDS
        }
        raw_dependencies = raw.get("depends_on", [])
        if not isinstance(raw_dependencies, list):
            raise _DecompositionOutputError(f"task {index} depends_on must be a list")

        dependencies: list[str] = []
        for dependency in raw_dependencies:
            if not isinstance(dependency, str) or not dependency.strip():
                raise _DecompositionOutputError(
                    f"task {index} depends_on must contain non-empty strings"
                )
            dependencies.append(dependency.strip())

        tasks.append(TaskItem(**values, depends_on=dependencies))

    _validate_dependencies(tasks)
    return tasks


def _validate_dependencies(tasks: list[TaskItem]) -> None:
    task_ids = [task.task_id for task in tasks]
    if len(task_ids) != len(set(task_ids)):
        raise _DecompositionOutputError("task_id values must be unique")

    known_ids = set(task_ids)
    indegree = {task_id: 0 for task_id in task_ids}
    dependents: dict[str, list[str]] = {task_id: [] for task_id in task_ids}
    for task in tasks:
        if len(task.depends_on) != len(set(task.depends_on)):
            raise _DecompositionOutputError("task dependency list contains duplicate entries")
        for dependency in task.depends_on:
            if dependency not in known_ids:
                raise _DecompositionOutputError("task dependency references an unknown task ID")
            if dependency == task.task_id:
                raise _DecompositionOutputError("task dependency cannot reference its own task ID")
            dependents[dependency].append(task.task_id)
            indegree[task.task_id] += 1

    ready = [task_id for task_id in task_ids if indegree[task_id] == 0]
    visited = 0
    while ready:
        current = ready.pop(0)
        visited += 1
        for dependent in dependents[current]:
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                ready.append(dependent)
    if visited != len(task_ids):
        raise _DecompositionOutputError("task dependency graph contains a cycle")


def _supports_think_false(provider: object) -> bool:
    try:
        parameters = inspect.signature(provider.generate).parameters.values()
    except (AttributeError, TypeError, ValueError):
        return False
    return any(
        parameter.name == "think" or parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in parameters
    )


async def _generate_structured(provider: object, system: str, user: str):
    kwargs: dict[str, object] = {"system": system, "user": user}
    if _supports_think_false(provider):
        kwargs["think"] = False
    return await provider.generate(**kwargs)


def _prompt(query: str, planning_context: str, retry_reason: str | None = None) -> str:
    retry_note = ""
    if retry_reason:
        retry_note = (
            "\n\nThe previous response failed structural validation because "
            f"{retry_reason}. Return a corrected object only."
        )
    return (
        f"USER REQUEST:\n{query}\n\n"
        "BOUNDED PLANNING CONTEXT (guidance only; not answer evidence):\n"
        f"{planning_context}\n\n"
        "Decompose only obligations stated or directly implied by the user request. "
        "Use the planning context only to clarify task boundaries. Do not add N/O, "
        "execution, retrieval, answer-domain evidence, or unstated requirements. "
        f"Return exactly one JSON object matching this schema: {_TASK_SCHEMA}."
        f"{retry_note}"
    )


def _safe_warning(exc: BaseException) -> str:
    if isinstance(exc, _DecompositionOutputError):
        return str(exc)
    return f"planner generation failed with {type(exc).__name__}"


def _failed_result(
    query: str,
    planning_evidence_ids: list[str],
    warning: str,
) -> DecompositionResult:
    return DecompositionResult(
        request=query,
        tasks=[],
        planning_evidence_ids=planning_evidence_ids,
        status="FAILED",
        warnings=[warning],
    )


async def decompose(
    provider,
    query: str,
    planning_context: str,
    metrics: RunMetrics,
) -> DecompositionResult:
    """Create a validated P-lite task plan from one bounded planning context.

    Only malformed structured output receives one repair attempt. Provider
    failures return a terminal failed result without exposing provider details.
    """

    if not isinstance(query, str) or not query.strip():
        safe_query = query if isinstance(query, str) else ""
        return _failed_result(safe_query, [], "request must be a non-empty string")
    if not isinstance(planning_context, str):
        return _failed_result(query, [], "planning context must be a string")

    request = query
    planning_evidence_ids = _extract_planning_evidence_ids(planning_context)
    system = (
        "TASK_DECOMPOSER. Return JSON only. Preserve atomic obligations and "
        "dependencies. Do not invent requirements. Use the supplied planning "
        "context only as bounded planning guidance."
    )
    retry_reason: str | None = None

    for attempt in range(2):
        try:
            result = await _generate_structured(
                provider,
                system,
                _prompt(request, planning_context, retry_reason),
            )
            metrics.add_usage(result.usage)
            tasks = _parse_tasks(_extract_json(result.text))
            return DecompositionResult(
                request=request,
                tasks=tasks,
                planning_evidence_ids=planning_evidence_ids,
                status="COMPLETE",
                warnings=[],
            )
        except _DecompositionOutputError as exc:
            retry_reason = _safe_warning(exc)
            if attempt == 1:
                return _failed_result(request, planning_evidence_ids, retry_reason)
        except Exception as exc:
            return _failed_result(request, planning_evidence_ids, _safe_warning(exc))

    return _failed_result(request, planning_evidence_ids, "planner output could not be validated")


__all__ = ["DecompositionResult", "TaskItem", "decompose"]
