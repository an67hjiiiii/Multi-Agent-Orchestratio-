from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.providers.fake import FakeProvider


class CoverageFakeProvider(FakeProvider):
    """Test double that satisfies the existing decomposer coverage contract."""

    recorded_prompts: list[str] = []

    async def generate(self, *, system: str, user: str):
        self.recorded_prompts.append(user)
        return await super().generate(system=system, user=user)

    def _tasks(self, user: str) -> list[dict]:
        tasks = super()._tasks(user)
        request = user.split("CURRENT REQUEST:\n", 1)[1].split("\n\n", 1)[0]
        for task in tasks:
            task["title"] = f"{request} — {task['title']}"
            task["expected_output"] = f"{request}. {task['expected_output']}"
            task["covers_obligations"] = ["O1"]
        return tasks


def register(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/auth/register",
        json={"email": email, "name": email, "password": "Password123!"},
    )
    assert response.status_code == 200
    return response.json()["user"]["user_id"]


def clients(tmp_path: Path, monkeypatch, mode: str = "LEXICAL") -> tuple[TestClient, TestClient, TestClient]:
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "dev")
    monkeypatch.setenv("PROVIDER", "fake")
    monkeypatch.setenv("RETRIEVAL_MODE", mode)
    monkeypatch.setenv("EMBEDDING_PROVIDER", "hash")
    if mode == "LEXICAL":
        monkeypatch.delenv("VECTOR_BACKEND", raising=False)
    else:
        monkeypatch.setenv("VECTOR_BACKEND", "memory")
    from app.research import pipeline as pipeline_module

    CoverageFakeProvider.recorded_prompts.clear()
    monkeypatch.setattr(pipeline_module, "get_provider", lambda _name: CoverageFakeProvider())
    application = create_app(data_dir=tmp_path / "data", runs_dir=tmp_path / "runs")
    return TestClient(application), TestClient(application), TestClient(application)


def import_private(client: TestClient, name: str, text: str) -> str:
    response = client.post(
        "/api/sources/text", json={"source_name": name, "text": text}
    )
    assert response.status_code == 200
    source = client.get(f"/api/sources/{response.json()['source_id']}")
    assert source.status_code == 200
    return source.json()["chunks"][0]["chunk_id"]


def test_anonymous_chat_requires_authentication(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "m0")
    monkeypatch.setenv("PROVIDER", "fake")
    client = TestClient(create_app(data_dir=tmp_path / "data", runs_dir=tmp_path / "runs"))

    response = client.post("/api/chat", json={"message": "private question"})

    assert response.status_code == 401
    assert response.json()["code"] == "AUTHENTICATION_REQUIRED"


@pytest.mark.parametrize("mode", ["LEXICAL", "VECTOR", "HYBRID"])
@pytest.mark.parametrize("condition", ["A", "B", "C"])
def test_chat_retrieval_is_owner_scoped_across_conditions(
    tmp_path: Path, monkeypatch, mode: str, condition: str
) -> None:
    first, second, _anonymous = clients(tmp_path, monkeypatch, mode)
    first_id = register(first, "first@example.test")
    second_id = register(second, "second@example.test")
    first_chunk = import_private(
        first, "first.md", "Zephyrquartz API authorization database query guidance. FIRST_PRIVATE_MARKER."
    )
    second_chunk = import_private(
        second, "second.md", "Zephyrquartz API authorization database query guidance for the second owner. SECOND_PRIVATE_MARKER."
    )
    request = {
        "message": "Review Zephyrquartz API authorization and database query guidance",
        "condition": condition,
        "provider": "fake",
    }

    first_response = first.post("/api/chat", json=request)
    first_prompts = list(CoverageFakeProvider.recorded_prompts)
    CoverageFakeProvider.recorded_prompts.clear()
    second_response = second.post("/api/chat", json=request)
    second_prompts = list(CoverageFakeProvider.recorded_prompts)
    assert first_response.status_code == second_response.status_code == 200
    first_run, second_run = first_response.json(), second_response.json()
    assert first_run["owner_id"] == first_id
    assert second_run["owner_id"] == second_id
    assert first_run["status"] != "FAILED"
    assert second_run["status"] != "FAILED"
    retrieval_stage = "vanilla_retrieval" if condition == "A" else "task_retrieval"
    first_events = [e for e in first_run["events"] if e["stage"] == retrieval_stage]
    second_events = [e for e in second_run["events"] if e["stage"] == retrieval_stage]
    assert first_events and second_events
    assert any(first_chunk in event["selected"] for event in first_events)
    assert any(second_chunk in event["selected"] for event in second_events)
    assert all(first_chunk not in event["candidates"] for event in second_events)
    assert all(second_chunk not in event["candidates"] for event in first_events)
    assert first_chunk not in json.dumps(second_run)
    assert second_chunk not in json.dumps(first_run)
    assert all("SECOND_PRIVATE_MARKER" not in prompt for prompt in first_prompts)
    assert all("FIRST_PRIVATE_MARKER" not in prompt for prompt in second_prompts)


def test_conversation_run_keeps_owner_scope(tmp_path: Path, monkeypatch) -> None:
    first, second, _anonymous = clients(tmp_path, monkeypatch)
    first_id = register(first, "conversation-first@example.test")
    second_id = register(second, "conversation-second@example.test")
    first_chunk = import_private(first, "first.md", "Zephyrquartz API contract guidance.")
    second_chunk = import_private(second, "second.md", "Other private API contract guidance.")
    first_conversation = first.post("/api/conversations", json={}).json()["conversation_id"]
    second_conversation = second.post("/api/conversations", json={}).json()["conversation_id"]
    assert second.get(f"/api/conversations/{first_conversation}").status_code == 404
    assert second.post(
        f"/api/conversations/{first_conversation}/messages",
        json={"message": "What is Zephyrquartz?"},
    ).status_code == 404

    first_response = first.post(
        f"/api/conversations/{first_conversation}/messages",
        json={"message": "What does the Zephyrquartz API contract say?", "provider": "fake"},
    )
    second_response = second.post(
        f"/api/conversations/{second_conversation}/messages",
        json={"message": "What does the Zephyrquartz API contract say?", "provider": "fake"},
    )
    assert first_response.status_code == second_response.status_code == 200
    first_run, second_run = first_response.json()["run"], second_response.json()["run"]
    assert first_run["owner_id"] == first_id
    assert second_run["owner_id"] == second_id
    assert first_chunk in json.dumps(first_run)
    assert first_chunk not in json.dumps(second_run)
    assert second_chunk not in json.dumps(first_run)


def test_run_reads_are_owner_scoped_and_legacy_runs_fail_closed(
    tmp_path: Path, monkeypatch
) -> None:
    first, second, anonymous = clients(tmp_path, monkeypatch)
    first_id = register(first, "run-first@example.test")
    register(second, "run-second@example.test")
    import_private(first, "first.md", "Zephyrquartz API contract guidance.")
    response = first.post(
        "/api/chat",
        json={"message": "What does Zephyrquartz API contract say?", "provider": "fake"},
    )
    assert response.status_code == 200
    run_id = response.json()["run_id"]
    assert response.json()["owner_id"] == first_id
    application = first.app
    assert application.state.api_runtime.run_store.get(run_id)["owner_id"] == first_id
    application.state.api_runtime.run_store.save({"run_id": "run_legacy"})

    for endpoint in (f"/api/runs/{run_id}", f"/api/runs/{run_id}/trace", f"/api/runs/{run_id}/evidence"):
        assert first.get(endpoint).status_code == 200
        assert second.get(endpoint).status_code == 404
        assert anonymous.get(endpoint).status_code == 401
    for endpoint in ("/api/runs", "/api/history"):
        owned = first.get(endpoint)
        assert owned.status_code == 200
        assert [item["run_id"] for item in owned.json()] == [run_id]
        assert second.get(endpoint).json() == []
        assert anonymous.get(endpoint).status_code == 401
    assert first.get("/api/runs/run_legacy").status_code == 404
    assert second.get("/api/runs/run_legacy").status_code == 404


def test_run_evidence_response_hides_foreign_and_unresolved_ids(
    tmp_path: Path, monkeypatch
) -> None:
    first, second, _anonymous = clients(tmp_path, monkeypatch)
    first_id = register(first, "evidence-first@example.test")
    register(second, "evidence-second@example.test")
    first_chunk = import_private(first, "first.md", "First user's private API evidence.")
    second_chunk = import_private(second, "second.md", "Second user's private API evidence.")
    first.app.state.api_runtime.run_store.save(
        {
            "run_id": "run_owned_evidence",
            "owner_id": first_id,
            "evidence_ids": [first_chunk, second_chunk, "src_unresolved_c0000"],
        }
    )

    response = first.get("/api/runs/run_owned_evidence/evidence")

    assert response.status_code == 200
    assert response.json()["evidence_ids"] == [first_chunk]
    assert response.json()["missing_ids"] == []
    assert [item["chunk_id"] for item in response.json()["items"]] == [first_chunk]
