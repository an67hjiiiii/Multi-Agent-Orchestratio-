"""Execute prepared research tasks without owning task planning or retrieval."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import asdict
from typing import Any

from app.core.types import RunMetrics, SourceChunk, Task
from app.research.contracts import WorkerResult
from app.research.worker import execute_task


async def execute_prepared_tasks(
    provider: Any,
    tasks: list[Task],
    *,
    resolve_task_evidence: Callable[[Task, str], Awaitable[list[SourceChunk]]],
    metrics: RunMetrics,
    event: Callable[..., None],
    max_run_tokens: int,
) -> list[WorkerResult]:
    """Run validated tasks in dependency order using their routed evidence.

    The evidence resolver remains responsible for the established retrieval and
    context-allocation policy. Exceptions deliberately propagate to
    ``RunCoordinator`` so its existing terminal-failure behavior is preserved.
    """

    completed: dict[str, WorkerResult] = {}
    results: list[WorkerResult] = []
    for task in tasks:
        event(
            "task_started",
            task_id=task.task_id,
            depends_on=list(task.depends_on),
        )
        try:
            dependency_context = " ".join(
                completed[dependency_id].answer
                for dependency_id in task.depends_on
                if dependency_id in completed
            )
            evidence = await resolve_task_evidence(task, dependency_context)
            generation_started = time.perf_counter()
            result = await execute_task(provider, task, evidence, metrics)
            metrics.generation_latency_ms += int(
                (time.perf_counter() - generation_started) * 1000
            )
        except Exception as exc:
            event(
                "task_failed",
                task_id=task.task_id,
                error_type=type(exc).__name__,
            )
            raise
        completed[task.task_id] = result
        results.append(result)
        event("task_completed", result=asdict(result))
        if metrics.input_tokens + metrics.output_tokens > max_run_tokens:
            event(
                "run_budget_exceeded",
                total_tokens=metrics.input_tokens + metrics.output_tokens,
            )
            break
    return results
