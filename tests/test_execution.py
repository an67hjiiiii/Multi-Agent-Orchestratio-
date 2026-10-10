import asyncio

import pytest

from app.core.types import ProviderResult, RunMetrics, SourceChunk, Task, Usage
from app.research.contracts import (
    WorkerLifecycleState,
    transition_worker_lifecycle,
)
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


def test_worker_lifecycle_accepts_only_pending_running_terminal_transitions():
    assert transition_worker_lifecycle(
        WorkerLifecycleState.PENDING, WorkerLifecycleState.RUNNING
    ) is WorkerLifecycleState.RUNNING
    assert transition_worker_lifecycle(
        WorkerLifecycleState.RUNNING, WorkerLifecycleState.FINISHED
    ) is WorkerLifecycleState.FINISHED
    assert transition_worker_lifecycle(
        WorkerLifecycleState.RUNNING, WorkerLifecycleState.FAILED
    ) is WorkerLifecycleState.FAILED

    with pytest.raises(ValueError, match="PENDING -> FINISHED"):
        transition_worker_lifecycle(
            WorkerLifecycleState.PENDING, WorkerLifecycleState.FINISHED
        )
    with pytest.raises(ValueError, match="FAILED -> RUNNING"):
        transition_worker_lifecycle(
            WorkerLifecycleState.FAILED, WorkerLifecycleState.RUNNING
        )


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
    assert [item["stage"] for item in events] == [
        "task_state_changed",
        "task_state_changed",
        "task_state_changed",
        "task_started",
        "task_state_changed",
        "task_completed",
        "task_state_changed",
        "task_started",
        "task_state_changed",
        "task_completed",
    ]
    assert [
        item["state"] for item in events if item["stage"] == "task_state_changed"
    ] == ["PENDING", "PENDING", "RUNNING", "FINISHED", "RUNNING", "FINISHED"]
    first_result = next(
        item["result"] for item in events if item["stage"] == "task_completed"
    )
    assert first_result == {
        "task_id": "T1",
        "domain": "api_architecture",
        "status": "COMPLETE",
        "answer": "grounded answer",
        "evidence_ids": ["chunk-1"],
        "citations": ["chunk-1"],
        "invalid_citations": [],
        "missing_information": [],
        "status_reason": "",
    }
    second_start = [
        item for item in events if item["stage"] == "task_started"
    ][1]
    assert second_start["task_id"] == "T2"
    assert second_start["depends_on"] == ["T1"]


def test_execution_preserves_budget_stop_after_current_worker_result():
    events: list[dict] = []

    async def resolve(_task: Task, _dependency_context: str) -> list[SourceChunk]:
        return _evidence()

    results = asyncio.run(
        execute_prepared_tasks(
            StubProvider(),
            [Task("T1", "First"), Task("T2", "Second")],
            resolve_task_evidence=resolve,
            metrics=RunMetrics(),
            event=lambda stage, **payload: events.append(
                {"stage": stage, **payload}
            ),
            max_run_tokens=1,
        )
    )

    assert [result.task_id for result in results] == ["T1"]
    states = [item for item in events if item["stage"] == "task_state_changed"]
    assert [(item["task_id"], item["state"]) for item in states] == [
        ("T1", "PENDING"),
        ("T2", "PENDING"),
        ("T1", "RUNNING"),
        ("T1", "FINISHED"),
    ]
    assert events[-1]["stage"] == "run_budget_exceeded"


def test_execution_preserves_worker_failures_for_run_coordinator():
    class FailingProvider:
        async def generate(self, *, system: str, user: str) -> ProviderResult:
            raise TimeoutError("provider timed out")

    async def resolve(_task: Task, _dependency_context: str) -> list[SourceChunk]:
        return _evidence()

    events: list[dict] = []

    with pytest.raises(TimeoutError, match="provider timed out"):
        asyncio.run(
            execute_prepared_tasks(
                FailingProvider(),
                [Task("T1", "First")],
                resolve_task_evidence=resolve,
                metrics=RunMetrics(),
                event=lambda stage, **payload: events.append(
                    {"stage": stage, **payload}
                ),
                max_run_tokens=100,
            )
        )

    assert [item["stage"] for item in events] == [
        "task_state_changed",
        "task_state_changed",
        "task_started",
        "task_state_changed",
        "task_failed",
    ]
    assert [
        item["state"] for item in events if item["stage"] == "task_state_changed"
    ] == ["PENDING", "RUNNING", "FAILED"]
    assert events[0]["task_id"] == events[-1]["task_id"] == "T1"
    assert events[-1]["error_type"] == "TimeoutError"
    assert "error" not in events[-1]


def test_execution_records_task_failure_when_evidence_resolution_raises():
    events: list[dict] = []

    async def fail_resolving_evidence(
        _task: Task, _dependency_context: str
    ) -> list[SourceChunk]:
        raise LookupError("retrieval failed")

    with pytest.raises(LookupError, match="retrieval failed"):
        asyncio.run(
            execute_prepared_tasks(
                StubProvider(),
                [Task("T1", "First")],
                resolve_task_evidence=fail_resolving_evidence,
                metrics=RunMetrics(),
                event=lambda stage, **payload: events.append(
                    {"stage": stage, **payload}
                ),
                max_run_tokens=100,
            )
        )

    assert [item["stage"] for item in events] == [
        "task_state_changed",
        "task_state_changed",
        "task_started",
        "task_state_changed",
        "task_failed",
    ]
    assert [
        item["state"] for item in events if item["stage"] == "task_state_changed"
    ] == ["PENDING", "RUNNING", "FAILED"]
    assert events[-1] == {
        "stage": "task_failed",
        "task_id": "T1",
        "error_type": "LookupError",
    }


def test_execution_completes_no_evidence_without_calling_worker_provider():
    class UnexpectedProvider:
        async def generate(self, *, system: str, user: str) -> ProviderResult:
            raise AssertionError("worker provider should not run without evidence")

    async def resolve(_task: Task, _dependency_context: str) -> list[SourceChunk]:
        return []

    metrics = RunMetrics()
    events: list[dict] = []

    results = asyncio.run(
        execute_prepared_tasks(
            UnexpectedProvider(),
            [Task("T1", "Review API")],
            resolve_task_evidence=resolve,
            metrics=metrics,
            event=lambda stage, **payload: events.append(
                {"stage": stage, **payload}
            ),
            max_run_tokens=100,
        )
    )

    assert len(results) == 1
    assert results[0].task_id == "T1"
    assert results[0].status == "NO_EVIDENCE"
    assert results[0].evidence_ids == []
    assert results[0].citations == []
    assert metrics.llm_calls == 0
    assert [
        item["state"] for item in events if item["stage"] == "task_state_changed"
    ] == ["PENDING", "RUNNING", "FINISHED"]
    assert events == [
        {
            "stage": "task_state_changed",
            "task_id": "T1",
            "previous_state": None,
            "state": "PENDING",
        },
        {
            "stage": "task_state_changed",
            "task_id": "T1",
            "previous_state": "PENDING",
            "state": "RUNNING",
        },
        {"stage": "task_started", "task_id": "T1", "depends_on": []},
        {
            "stage": "task_state_changed",
            "task_id": "T1",
            "previous_state": "RUNNING",
            "state": "FINISHED",
        },
        {
            "stage": "task_completed",
            "result": {
                "task_id": "T1",
                "domain": "api_architecture",
                "status": "NO_EVIDENCE",
                "answer": "Chưa tìm thấy evidence phù hợp cho task này.",
                "evidence_ids": [],
                "citations": [],
                "invalid_citations": [],
                "missing_information": ["relevant evidence"],
                "status_reason": "",
            },
        },
    ]
