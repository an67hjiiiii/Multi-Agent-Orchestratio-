from fastapi.testclient import TestClient

from app.auth.store import AuthStore
from app.main import app
from app import main as main_module


def _create_users(tmp_path):
    store = AuthStore(tmp_path / "auth")
    user_a = store.register(
        email="owner-a@example.test", password="correct-horse-battery"
    )
    user_b = store.register(
        email="owner-b@example.test", password="correct-horse-battery"
    )
    token_a, _ = store.create_session(user_a["user_id"])
    token_b, _ = store.create_session(user_b["user_id"])
    app.state.auth_store = store
    return (
        {"Authorization": f"Bearer {token_a}"},
        {"Authorization": f"Bearer {token_b}"},
    )


def test_sources_and_chunks_are_private_to_the_authenticated_owner(tmp_path, monkeypatch):
    monkeypatch.setattr(main_module, "DATA_DIR", str(tmp_path / "data"))
    headers_a, headers_b = _create_users(tmp_path)

    with TestClient(app) as client:
        uploaded = client.post(
            "/api/sources/text",
            headers=headers_a,
            json={
                "source_name": "private-a.md",
                "text": "Only owner A can inspect this source evidence.",
            },
        )
        source_id = uploaded.json()["source_id"]
        source_a = client.get(f"/api/sources/{source_id}", headers=headers_a)
        source_b = client.get(f"/api/sources/{source_id}", headers=headers_b)
        list_b = client.get("/api/sources", headers=headers_b)
        chunk_id = source_a.json()["chunks"][0]["chunk_id"]
        chunk_b = client.get(f"/api/chunks/{chunk_id}", headers=headers_b)
        anonymous = client.get("/api/sources")

    assert uploaded.status_code == 200
    assert source_a.status_code == 200
    assert source_b.status_code == 404
    assert list_b.json()["sources"] == []
    assert chunk_b.status_code == 404
    assert anonymous.status_code == 401


def test_chat_and_run_records_use_the_calling_users_private_sources(tmp_path, monkeypatch):
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "m0")
    monkeypatch.setattr(main_module, "DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr(main_module, "RUNS_DIR", str(tmp_path / "runs"))
    headers_a, headers_b = _create_users(tmp_path)

    with TestClient(app) as client:
        client.post(
            "/api/sources/text",
            headers=headers_a,
            json={
                "source_name": "private-a.md",
                "text": "Owner A's API validates requests and returns errors.",
            },
        )
        run = client.post(
            "/api/chat",
            headers=headers_a,
            json={"message": "What does the API do?", "condition": "A", "provider": "fake"},
        )
        run_id = run.json()["run_id"]
        runs_b = client.get("/api/runs", headers=headers_b)
        run_b = client.get(f"/api/runs/{run_id}", headers=headers_b)

    assert run.status_code == 200
    assert run.json()["status"] == "COMPLETE"
    assert runs_b.json() == []
    assert run_b.status_code == 404
