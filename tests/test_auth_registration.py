from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


def make_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "m0")
    monkeypatch.setenv("PROVIDER", "fake")
    monkeypatch.delenv("VECTOR_BACKEND", raising=False)
    monkeypatch.delenv("LOCAL_AUTH_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("LOCAL_AUTH_ADMIN_PASSWORD", raising=False)
    return TestClient(
        create_app(
            data_dir=tmp_path / "data",
            runs_dir=tmp_path / "runs",
            frontend_dist_dir=tmp_path / "missing-frontend",
        )
    )


def test_public_registration_forces_user_role_and_hashes_password(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client(tmp_path, monkeypatch)
    base_payload = {
        "email": "registration@example.test",
        "name": "Registration",
        "password": "Password123!",
    }

    registered = client.post(
        "/api/auth/register",
        json={**base_payload, "role": "ADMIN"},
    )

    assert registered.status_code == 200
    assert registered.json()["user"]["role"] == "USER"
    assert "password" not in registered.json()
    assert "password_hash" not in registered.json()

    auth_path = tmp_path / "data" / "auth.json"
    stored_auth = json.loads(auth_path.read_text(encoding="utf-8"))
    assert len(stored_auth["users"]) == 1
    password_hash = stored_auth["users"][0]["password_hash"]
    assert password_hash.startswith("pbkdf2_sha256$")
    assert password_hash != base_payload["password"]
    assert base_payload["password"] not in json.dumps(stored_auth)


def test_duplicate_registration_is_rejected_without_creating_a_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client(tmp_path, monkeypatch)
    payload = {
        "email": "duplicate@example.test",
        "name": "Duplicate",
        "password": "Password123!",
    }

    registered = client.post("/api/auth/register", json=payload)
    assert registered.status_code == 200
    assert client.post("/api/auth/logout").status_code == 200

    duplicate = client.post("/api/auth/register", json=payload)

    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "ACCOUNT_EXISTS"
    assert "set-cookie" not in duplicate.headers
    session = client.get("/api/auth/session")
    assert session.status_code == 200
    assert session.json()["authenticated"] is False
    assert session.json()["user"] is None
    assert client.get("/api/auth/me").status_code == 401

    stored_auth = json.loads((tmp_path / "data" / "auth.json").read_text(encoding="utf-8"))
    assert len(stored_auth["users"]) == 1


@pytest.mark.parametrize(
    ("payload", "expected_status"),
    [
        (
            {
                "email": "not-an-email",
                "name": "Invalid Email",
                "password": "Password123!",
            },
            400,
        ),
        (
            {
                "email": "short-password@example.test",
                "name": "Short Password",
                "password": "short",
            },
            400,
        ),
        ({"email": "missing-password@example.test", "name": "Missing Password"}, 422),
    ],
)
def test_public_registration_validates_email_and_password(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    payload: dict[str, str],
    expected_status: int,
) -> None:
    client = make_client(tmp_path, monkeypatch)

    response = client.post("/api/auth/register", json=payload)

    assert response.status_code == expected_status
