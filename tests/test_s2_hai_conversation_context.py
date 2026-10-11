from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

from app import main as main_module
from app.auth.store import AuthStore
from app.main import app
from app.research.conversation_context import build_conversation_context
from app.research.pipeline import ResearchPipeline
from app.storage.conversation_store import ConversationStore
from app.storage.run_store import RunStore
from app.storage.source_store import SourceStore


def test_conversation_context_is_bounded_and_trace_is_not_rag_evidence():
    conversation = {
        "messages": [
            {"message_id": f"m{i}", "role": "USER", "content": "x" * 20}
            for i in range(10)
        ]
    }
    context = build_conversation_context(conversation, max_messages=3, max_chars=35)
    assert len(context.message_ids) <= 3
    assert len(context.text) <= 35
    assert context.truncated is True
    assert context.to_trace()["is_rag_evidence"] is False


def test_pipeline_persists_same_conversation_context_trace(tmp_path, monkeypatch):
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "m0")
    conversations = ConversationStore(tmp_path / "conversations")
    conversation = conversations.create("same conversation")
    previous = conversations.add_message(
        conversation["conversation_id"], "USER", "Earlier request"
    )
    sources = SourceStore(str(tmp_path / "data"))
    sources.import_text("guide.md", "The earlier request concerns API evidence.")
    run = asyncio.run(
        ResearchPipeline(sources, RunStore(str(tmp_path / "runs"))).run(
            "Follow-up request",
            "A",
            "fake",
            conversation_id=conversation["conversation_id"],
            conversation_context=build_conversation_context(
                conversations.get(conversation["conversation_id"])
            ),
        )
    )
    assert run["conversation_id"] == conversation["conversation_id"]
    assert run["conversation_context"]["message_ids"] == [previous["message_id"]]
    context_event = next(event for event in run["events"] if event["stage"] == "conversation_context")
    assert context_event["is_rag_evidence"] is False


def test_api_builds_context_from_only_prior_messages(tmp_path, monkeypatch):
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "m0")
    monkeypatch.setattr(main_module, "DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr(main_module, "RUNS_DIR", str(tmp_path / "runs"))
    auth = AuthStore(tmp_path / "auth")
    user = auth.register(email="context@example.test", password="long-enough-password")
    token, _ = auth.create_session(user["user_id"])
    app.state.auth_store = auth
    headers = {"Authorization": f"Bearer {token}"}

    with TestClient(app) as client:
        uploaded = client.post(
            "/api/sources/text",
            headers=headers,
            json={"source_name": "guide.md", "text": "API evidence is available."},
        )
        assert uploaded.status_code == 200
        first = client.post(
            "/api/chat",
            headers=headers,
            json={"message": "First request", "condition": "A", "provider": "fake"},
        )
        assert first.status_code == 200
        conversation_id = first.json()["conversation_id"]
        second = client.post(
            "/api/chat",
            headers=headers,
            json={
                "message": "Follow-up request",
                "conversation_id": conversation_id,
                "condition": "A",
                "provider": "fake",
            },
        )
        assert second.status_code == 200

        conversation = client.get(
            f"/api/conversations/{conversation_id}", headers=headers
        )
        assert conversation.status_code == 200

    trace = second.json()["conversation_context"]
    assert trace["message_count"] == 2
    assert trace["is_rag_evidence"] is False
    assert len(trace["message_ids"]) == 2
    assert conversation.json()["messages"][-1]["message_id"] not in trace["message_ids"]
