from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def make_client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "m0")
    monkeypatch.setenv("PROVIDER", "fake")
    return TestClient(
        create_app(
            data_dir=tmp_path / "data",
            runs_dir=tmp_path / "runs",
        )
    )


def test_api_boundary_preserves_static_frontend_and_m0_health(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)

    root = client.get("/")
    assert root.status_code == 200
    assert "Local Multi-Agent RAG" in root.text

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["allowed_conditions"] == ["A"]
    assert health.json()["implementation_profile"] == "m0"


def test_api_boundary_imports_sources_and_runs_m0_chat(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)

    imported = client.post(
        "/api/sources/text",
        json={
            "source_name": "api.md",
            "text": "The API contract defines request validation and error responses.",
        },
    )
    assert imported.status_code == 200
    assert imported.json()["chunks_added"] == 1

    run_response = client.post(
        "/api/chat",
        json={"message": "What does the API contract define?", "condition": "A", "provider": "fake"},
    )
    assert run_response.status_code == 200
    run = run_response.json()
    assert run["status"] == "COMPLETE"
    assert run["condition"] == "A"
    assert client.get(f"/api/runs/{run['run_id']}").json()["run_id"] == run["run_id"]
    assert client.get("/api/runs").json()[0]["run_id"] == run["run_id"]


def test_api_boundary_keeps_validation_errors_explicit(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)

    blank_chat = client.post("/api/chat", json={"message": "   "})
    assert blank_chat.status_code == 400
    assert blank_chat.json()["detail"] == "message is required"

    unsupported_condition = client.post(
        "/api/chat",
        json={"message": "anything", "condition": "B", "provider": "fake"},
    )
    assert unsupported_condition.status_code == 400
    assert "not available in profile m0" in unsupported_condition.json()["detail"]

    missing_source = client.get("/api/sources/not-found")
    assert missing_source.status_code == 404
    assert missing_source.json()["detail"] == "source not found"


def test_api_boundary_accepts_utf8_file_upload(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)

    response = client.post(
        "/api/sources/file",
        files={"file": ("notes.md", "Nội dung có dấu.", "text/markdown")},
    )
    assert response.status_code == 200
    assert response.json()["source_name"] == "notes.md"
