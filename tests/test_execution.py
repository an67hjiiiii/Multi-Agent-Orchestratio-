import asyncio

import pytest

from app.core.types import ProviderResult, RunMetrics, SourceChunk, Task, Usage
from app.research.execution import execute_prepared_tasks


class StubProvider:
    model = "stub"

    async def generate(self, *, system: str, user: str) -> ProviderResult:
        return ProviderResult(
            text='{"status":"COMPLETE","answer":"grounded answer","citations":["E1"]}',
            usage=Usage(1, 1),
            model=self.model,
        )


def _evidence() -> list[SourceChunk]:
    return [SourceChunk("chunk-1", "source-1", "api.md", "API evidence.", 0)]


def test_execution_uses_completed_dependency_answers_for_routed_context():
    contexts: list[str] = []
    events: list[dict] = []

    async def resolve(task: Task, dependency_context: str) -> list[SourceChunk]:
        contexts.append(dependency_context)
        return _evidence()

    def event(stage: str, **payload) -> None:
        events.append({"stage": stage, **payload})

    results = asyncio.run(
        execute_prepared_tasks(
            StubProvider(),
            [
                Task("T1", "Review API", domain="api_architecture"),
                Task("T2", "Summarize API", domain="api_architecture", depends_on=["T1"]),
            ],
            resolve_task_evidence=resolve,
            metrics=RunMetrics(),
            event=event,
            max_run_tokens=100,
        )
    )

    assert [result.task_id for result in results] == ["T1", "T2"]
    assert contexts == ["", "grounded answer"]
    assert [item["stage"] for item in events] == ["task_completed", "task_completed"]


def test_execution_preserves_budget_stop_after_current_worker_result():
    events: list[str] = []

    async def resolve(_task: Task, _dependency_context: str) -> list[SourceChunk]:
        return _evidence()

    results = asyncio.run(
        execute_prepared_tasks(
            StubProvider(),
            [Task("T1", "First"), Task("T2", "Second")],
            resolve_task_evidence=resolve,
            metrics=RunMetrics(),
            event=lambda stage, **_payload: events.append(stage),
            max_run_tokens=1,
        )
    )

    assert [result.task_id for result in results] == ["T1"]
    assert events == ["task_completed", "run_budget_exceeded"]


def test_execution_preserves_worker_failures_for_run_coordinator():
    class FailingProvider:
        async def generate(self, *, system: str, user: str) -> ProviderResult:
            raise TimeoutError("provider timed out")

    async def resolve(_task: Task, _dependency_context: str) -> list[SourceChunk]:
        return _evidence()

    with pytest.raises(TimeoutError, match="provider timed out"):
        asyncio.run(
            execute_prepared_tasks(
                FailingProvider(),
                [Task("T1", "First")],
                resolve_task_evidence=resolve,
                metrics=RunMetrics(),
                event=lambda *_args, **_kwargs: None,
                max_run_tokens=100,
            )
        )
