from __future__ import annotations

import asyncio

from app.core.api_runtime import ApiRuntime
from app.research.conversation_context import ConversationContext
from app.run.contracts import Run


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
