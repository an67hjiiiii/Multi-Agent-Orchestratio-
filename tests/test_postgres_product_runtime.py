from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app import main as main_module
from app.auth.store import InvalidSessionError
from app.storage.postgres.config import create_postgres_engine, create_session_factory
from app.storage.postgres.runtime import (
    PostgresAuthStore,
    PostgresConversationStore,
    PostgresRunStore,
    PostgresSourceStore,
)


@pytest.mark.skipif(
    os.getenv("CAP1_POSTGRES_RUNTIME_TEST") != "1",
    reason="requires a dedicated migrated PostgreSQL test database",
)
def test_product_api_persists_all_owner_state_across_engine_reconnect(monkeypatch):
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "m0")
    engine = create_postgres_engine()
    factory = create_session_factory(engine)
    monkeypatch.setattr(main_module, "STORAGE_BACKEND", "postgres")
    monkeypatch.setattr(main_module.app.state, "session_factory", factory)
    monkeypatch.setattr(main_module.app.state, "auth_store", PostgresAuthStore(factory))

    with TestClient(main_module.app) as client:
        anonymous = client.post("/api/chat", json={
            "message": "Private request.", "condition": "Z", "provider": "fake",
        })
        assert anonymous.status_code == 401
        registered_a = client.post("/api/auth/register", json={
            "email": "pg-a@example.test", "password": "long-enough-password",
        })
        registered_b = client.post("/api/auth/register", json={
            "email": "pg-b@example.test", "password": "long-enough-password",
        })
        assert registered_a.status_code == registered_b.status_code == 201
        login_a = client.post("/api/auth/login", json={
            "email": "pg-a@example.test", "password": "long-enough-password",
        }).json()
        login_b = client.post("/api/auth/login", json={
            "email": "pg-b@example.test", "password": "long-enough-password",
        }).json()
        headers_a = {"Authorization": f"Bearer {login_a['access_token']}"}
        headers_b = {"Authorization": f"Bearer {login_b['access_token']}"}

        invalid = client.post("/api/chat", headers=headers_a, json={
            "message": "This condition is unavailable.", "condition": "Z", "provider": "fake",
        })
        assert invalid.status_code == 400
        assert client.get("/api/conversations", headers=headers_a).json() == []

        uploaded = client.post("/api/sources/text", headers=headers_a, json={
            "source_name": "private.txt", "text": "Private source evidence for owner A.",
        })
        source_id = uploaded.json()["source_id"]
        chunk_id = client.get(f"/api/sources/{source_id}", headers=headers_a).json()["chunks"][0]["chunk_id"]
        assert client.get(f"/api/sources/{source_id}", headers=headers_b).status_code == 404
        assert client.get(f"/api/chunks/{chunk_id}", headers=headers_b).status_code == 404

        run_response = client.post("/api/chat", headers=headers_a, json={
            "message": "Summarize the source evidence.", "condition": "A", "provider": "fake",
        })
        assert run_response.status_code == 200
        run = run_response.json()
        conversation_id = run["conversation_id"]
        assert run["status"] in {"COMPLETE", "PARTIAL", "NO_EVIDENCE"}
        conversation = client.get(f"/api/conversations/{conversation_id}", headers=headers_a).json()
        assert [message["role"] for message in conversation["messages"]] == ["USER", "ASSISTANT"]
        assert client.get(f"/api/conversations/{conversation_id}", headers=headers_b).status_code == 404
        assert client.get(f"/api/runs/{run['run_id']}", headers=headers_b).status_code == 404
        assert client.post("/api/auth/logout", headers=headers_a).status_code == 200

    engine.dispose()
    engine = create_postgres_engine()
    factory = create_session_factory(engine)
    owner_id = registered_a.json()["user"]["user_id"]
    auth_store = PostgresAuthStore(factory)
    assert auth_store.resolve(login_b["access_token"])["user_id"] == registered_b.json()["user"]["user_id"]
    with pytest.raises(InvalidSessionError):
        auth_store.resolve(login_a["access_token"])
    assert PostgresSourceStore(factory, owner_id).source(source_id) is not None
    assert PostgresRunStore(factory, owner_id).get(run["run_id"])["status"] == run["status"]
    restored = PostgresConversationStore(factory, owner_id).get(conversation_id)
    assert len(restored["messages"]) == 2
    assert restored["messages"][1]["run_id"] == run["run_id"]
    engine.dispose()
