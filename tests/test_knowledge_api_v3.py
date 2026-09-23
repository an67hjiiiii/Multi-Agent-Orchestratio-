from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def _client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "m0")
    monkeypatch.setenv("PROVIDER", "fake")
    monkeypatch.setenv("RETRIEVAL_MODE", "HYBRID")
    monkeypatch.setenv("VECTOR_BACKEND", "memory")
    client = TestClient(
        create_app(
            data_dir=tmp_path / "data",
            runs_dir=tmp_path / "runs",
            frontend_dist_dir=tmp_path,
        )
    )
    registered = client.post(
        "/api/auth/register",
        json={"email": "knowledge@example.test", "name": "Knowledge", "password": "Password123!"},
    )
    assert registered.status_code == 200
    return client


def test_api_exposes_hybrid_status_and_indexes_imported_text(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    config = client.get("/api/config")
    assert config.status_code == 200
    assert config.json()["retrieval_mode"] == "HYBRID"

    imported = client.post(
        "/api/kb/import/text",
        json={
            "source_name": "auth.md",
            "text": "Authentication verifies identity before authorization checks permission.",
        },
    )
    assert imported.status_code == 200
    assert imported.json()["retrieval_backend"] == "memory"
    assert imported.json()["vector_indexed_chunks"] == 1

    status = client.get("/api/kb/status")
    assert status.status_code == 200
    assert status.json()["retrieval_mode"] == "HYBRID"
    assert status.json()["index_status"] == "READY"

    search = client.get("/api/kb/search", params={"query": "verify identity"})
    assert search.status_code == 200
    assert search.json()["results"]
