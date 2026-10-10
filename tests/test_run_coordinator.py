from __future__ import annotations

import asyncio

from app.core.api_runtime import ApiRuntime
from app.core.types import SourceChunk, Task
from app.research.conversation_context import ConversationContext
from app.research.execution import execute_prepared_tasks
from app.run.coordinator import RunCoordinator
from app.run.contracts import Run
from app.storage.run_store import RunStore
from app.storage.source_store import SourceStore


def test_run_coordinator_persists_the_existing_run_shape_and_context(tmp_path, monkeypatch):
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "m0")
    monkeypatch.setenv("PROVIDER", "fake")
    runtime = ApiRuntime.from_env(
        data_dir=tmp_path / "data",
        runs_dir=tmp_path / "runs",
    )
    runtime.source_store.import_text(
        "coordinator.md",
        "Request validation and API error responses are required.",
    )

    result = asyncio.run(
        runtime.run_coordinator.execute(
            "What does the source require?",
            "A",
            "fake",
            conversation_context=ConversationContext(
                text="[USER] Earlier context",
                message_ids=("message_1",),
            ),
            conversation_id="conversation_1",
        )
    )

    persisted = runtime.run_store.get(result["run_id"])
    assert persisted == result
    assert Run.from_mapping(result).to_dict() == result
    assert result["conversation_id"] == "conversation_1"
    assert "owner_id" not in result
    assert result["conversation_context"]["message_ids"] == ["message_1"]
    assert [event["stage"] for event in result["events"]][:2] == [
        "run_started",
        "conversation_context",
    ]
    assert result["events"][-1]["stage"] == "run_finished"


def test_worker_timeout_is_persisted_as_terminal_failed_run(tmp_path, monkeypatch):
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "m1")
    monkeypatch.setenv("PROVIDER", "fake")

    class TimeoutProvider:
        name = "fake"
        model = "fake-timeout"

        async def generate(self, *, system: str, user: str):
            raise TimeoutError("worker provider timed out")

    provider = TimeoutProvider()

    async def process(
        _query,
        _condition,
        resolved_provider,
        _config,
        _flags,
        _conversation_context,
        metrics,
        event,
        _retrieval_metadata,
        **_kwargs,
    ):
        task = Task("T1", "Review API request validation", domain="api_architecture")

        async def resolve_task_evidence(_task, _dependency_context):
            return [SourceChunk("chunk-1", "source-1", "api.md", "API evidence.", 0)]

        await execute_prepared_tasks(
            resolved_provider,
            [task],
            resolve_task_evidence=resolve_task_evidence,
            metrics=metrics,
            event=event,
            max_run_tokens=100,
        )
        return "COMPLETE", "", [task], [], True

    async def retrieval_metadata():
        return {"retrieval_backend": "memory"}

    coordinator = RunCoordinator(
        SourceStore(str(tmp_path / "data")),
        RunStore(str(tmp_path / "runs")),
        process=process,
        retrieval_metadata=retrieval_metadata,
        provider_resolver=lambda _name: provider,
        scoring_versions={},
        planning_retrieval_scoring_version="test",
        retrieval_scoring_version="test",
        domain_ranking_version="test",
        retrieval_metadata_defaults={"retrieval_backend": "memory"},
    )

    result = asyncio.run(
        coordinator.execute(
            "Review API request validation",
            "B",
            "fake",
        )
    )

    persisted = coordinator.run_store.get(result["run_id"])
    failures = [event for event in result["events"] if event["stage"] == "run_failed"]

    assert result["status"] == "FAILED"
    assert persisted == result
    assert len(failures) == 1
    assert failures[0]["error_type"] == "TimeoutError"
    assert failures[0]["error"] == "worker provider timed out"
    lifecycle_stages = {"task_started", "task_failed", "run_failed"}
    assert [
        event["stage"]
        for event in result["events"]
        if event["stage"] in lifecycle_stages
    ] == ["task_started", "task_failed", "run_failed"]
    failed_task = next(
        event for event in result["events"] if event["stage"] == "task_failed"
    )
    assert failed_task["task_id"] == "T1"
    assert failed_task["error_type"] == "TimeoutError"
    assert result["effective_config"]["flags"] == {"P": False, "N": False, "O": False}
