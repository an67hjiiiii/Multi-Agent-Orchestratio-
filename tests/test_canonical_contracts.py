from app.conversation.contracts import Conversation, Message
from app.core.types import Citation, Evidence, SourceChunk
from app.research.contracts import FinalResult, ValidationResult, planning_task_to_runtime
from app.research.task_schema import DecompositionResult, TaskItem
from app.run.contracts import Run


def test_planning_task_adapter_preserves_planning_metadata_and_dependencies():
    item = TaskItem(
        task_id="T2",
        title="Authorize the request",
        objective="Check permissions",
        expected_output="A permission decision",
        domain="security",
        role_profile="security_reviewer",
        depends_on=["T1"],
        covers_obligations=["authz"],
    )

    task = planning_task_to_runtime(item)
    assert task.task_id == "T2"
    assert task.goal == "Check permissions"
    assert task.title == "Authorize the request"
    assert task.expected_output == "A permission decision"
    assert task.role_profile == "security_reviewer"
    assert task.covers_obligations == ["authz"]
    assert task.depends_on == ["T1"]


def test_run_round_trip_preserves_known_and_unknown_trace_fields():
    raw = {
        "run_id": "run_contract",
        "status": "COMPLETE",
        "events": [{"stage": "done"}],
        "metrics": {"latency_ms": 4},
        "future_trace": {"version": 1},
    }

    typed = Run.from_mapping(raw)
    payload = typed.to_dict()
    assert payload["run_id"] == "run_contract"
    assert payload["events"] == [{"stage": "done"}]
    assert payload["future_trace"] == {"version": 1}
    assert payload["tasks"] == []


def test_conversation_and_message_round_trip_preserve_schema_and_extensions():
    raw = {
        "schema_version": "conversation-v9",
        "conversation_id": "conv_1",
        "owner_user_id": "owner",
        "title": "Thread",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:01:00Z",
        "messages": [{
            "message_id": "msg_1",
            "conversation_id": "conv_1",
            "role": "USER",
            "content": "hello",
            "created_at": "2026-01-01T00:00:00Z",
            "run_id": None,
            "message_extension": "kept",
        }],
        "conversation_extension": True,
    }

    conversation = Conversation.from_mapping(raw)
    assert conversation.to_dict() == raw
    assert conversation.to_public_dict()["messages"][0]["message_extension"] == "kept"
    assert Message.from_mapping(raw["messages"][0]).to_dict() == raw["messages"][0]


def test_evidence_citation_and_result_contracts_are_explicit():
    assert Evidence is SourceChunk
    assert Citation("chunk-1").to_value() == "chunk-1"

    final = FinalResult.from_mapping({
        "status": "PARTIAL",
        "answer": "grounded",
        "citations": ["chunk-1"],
        "missing_information": ["SLA"],
    })
    assert final.to_dict()["status"] == "PARTIAL"
    assert final.to_dict()["citations"] == ["chunk-1"]

    decomposition = DecompositionResult(
        request="check auth",
        tasks=[],
        planning_evidence_ids=[],
        status="NO_EVIDENCE",
        warnings=["no plan"],
        missing_obligations=["auth"],
        coverage_validation_reason="missing evidence",
    )
    validation = ValidationResult.from_decomposition(decomposition)
    assert validation.status == "NO_EVIDENCE"
    assert validation.missing_obligations == ["auth"]
    assert validation.reason == "missing evidence"
