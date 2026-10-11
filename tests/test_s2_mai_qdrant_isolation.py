import pytest
from fastapi.testclient import TestClient

from app import main as main_module
from app.auth.store import AuthStore
from app.main import app


def test_user_b_chat_cannot_retrieve_user_a_qdrant_evidence(tmp_path, monkeypatch):
    pytest.importorskip("qdrant_client")
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "m0")
    monkeypatch.setattr(main_module, "STORAGE_BACKEND", "file")
    monkeypatch.setattr(main_module, "DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr(main_module, "RUNS_DIR", str(tmp_path / "runs"))
    monkeypatch.setattr(main_module, "VECTOR_BACKEND", "qdrant")
    monkeypatch.setattr(main_module, "VECTOR_INDEX_PATH", str(tmp_path / "qdrant"))
    monkeypatch.setattr(main_module, "VECTOR_COLLECTION", "s2-owner-isolation")
    monkeypatch.setattr(main_module, "VECTOR_SIZE", "8")
    monkeypatch.setattr(main_module, "_derived_vector_store", None)
    monkeypatch.setattr(main_module, "_derived_vector_store_backend", None)
    auth = AuthStore(tmp_path / "auth")
    owner_a = auth.register(
        email="vector-owner-a@example.test", password="long-enough-password"
    )
    owner_b = auth.register(
        email="vector-owner-b@example.test", password="long-enough-password"
    )
    token_a, _ = auth.create_session(owner_a["user_id"])
    token_b, _ = auth.create_session(owner_b["user_id"])
    app.state.auth_store = auth
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    try:
        with TestClient(app) as client:
            uploaded = client.post(
                "/api/sources/text",
                headers=headers_a,
                json={
                    "source_name": "private-a.md",
                    "text": "Owner A secret retrieval evidence alpha.",
                },
            )
            run = client.post(
                "/api/chat",
                headers=headers_b,
                json={
                    "message": "Tell me Owner A secret retrieval evidence alpha.",
                    "condition": "A",
                    "provider": "fake",
                },
            )

        assert uploaded.status_code == 200
        assert run.status_code == 200
        result = run.json()
        retrieval = next(
            event for event in result["events"] if event["stage"] == "vanilla_retrieval"
        )
        assert result["status"] == "NO_EVIDENCE"
        assert retrieval["retrieval_backend"] == "qdrant"
        assert retrieval["candidates"] == []
        assert result["task_results"][0]["evidence_ids"] == []
        assert result["task_results"][0]["citations"] == []
    finally:
        vector_store = main_module._derived_vector_store
        if vector_store is not None and hasattr(vector_store.client, "close"):
            vector_store.client.close()
        monkeypatch.setattr(main_module, "_derived_vector_store", None)
        monkeypatch.setattr(main_module, "_derived_vector_store_backend", None)
