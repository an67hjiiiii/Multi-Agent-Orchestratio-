from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def register(client: TestClient, email: str) -> None:
    response = client.post(
        "/api/auth/register",
        json={"email": email, "name": email, "password": "Password123!"},
    )
    assert response.status_code == 200


def test_source_reads_are_scoped_to_the_importing_local_user(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "m0")
    monkeypatch.setenv("PROVIDER", "fake")
    application = create_app(data_dir=tmp_path / "data", runs_dir=tmp_path / "runs")
    owner = TestClient(application)
    other_user = TestClient(application)
    register(owner, "owner@example.test")
    register(other_user, "other@example.test")

    imported = owner.post(
        "/api/sources/text",
        json={"source_name": "private.md", "text": "Only the owner may inspect this source."},
    )
    assert imported.status_code == 200
    source_id = imported.json()["source_id"]
    owner_source = owner.get(f"/api/sources/{source_id}")
    chunk_id = owner_source.json()["chunks"][0]["chunk_id"]

    assert owner_source.status_code == 200
    assert owner.get("/api/sources").json()["sources"][0]["source_id"] == source_id
    assert owner.get(f"/api/chunks/{chunk_id}").status_code == 200
    assert other_user.get(f"/api/sources/{source_id}").status_code == 404
    assert other_user.get(f"/api/chunks/{chunk_id}").status_code == 404
    assert other_user.get("/api/sources").json()["sources"] == []
