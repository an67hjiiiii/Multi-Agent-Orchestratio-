from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


def make_registration_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "m0")
    monkeypatch.setenv("PROVIDER", "fake")
    monkeypatch.delenv("VECTOR_BACKEND", raising=False)
    monkeypatch.delenv("LOCAL_AUTH_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("LOCAL_AUTH_ADMIN_PASSWORD", raising=False)
    return TestClient(
        create_app(
            data_dir=tmp_path / "data",
            runs_dir=tmp_path / "runs",
        )
    )


def test_registration_creates_user_and_authenticated_session(tmp_path, monkeypatch):
    client = make_registration_client(tmp_path, monkeypatch)

    response = client.post(
        "/api/auth/register",
        json={
            "email": "new-user@example.test",
            "name": "New User",
            "password": "Password123!",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["authenticated"] is True
    assert payload["user"]["email"] == "new-user@example.test"
    assert payload["user"]["name"] == "New User"
    assert payload["user"]["role"] == "USER"
    assert "password_hash" not in payload["user"]
    assert payload["access_token"] == payload["token"]
    assert "session_token=" in response.headers["set-cookie"]

    session = client.get("/api/auth/session").json()
    assert session["authenticated"] is True
    assert session["user"]["user_id"] == payload["user"]["user_id"]


def test_registration_rejects_duplicate_email(tmp_path, monkeypatch):
    client = make_registration_client(tmp_path, monkeypatch)
    request = {
        "email": "duplicate@example.test",
        "password": "Password123!",
    }

    first = client.post("/api/auth/register", json=request)
    duplicate = client.post("/api/auth/register", json=request)

    assert first.status_code == 200
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "ACCOUNT_EXISTS"


@pytest.mark.parametrize(
    ("request", "status_code", "error_code"),
    [
        ({"email": "missing-password@example.test"}, 422, "VALIDATION_ERROR"),
        ({"password": "Password123!"}, 400, "INVALID_REGISTRATION"),
    ],
)
def test_registration_rejects_missing_required_fields(
    tmp_path,
    monkeypatch,
    request,
    status_code,
    error_code,
):
    client = make_registration_client(tmp_path, monkeypatch)

    response = client.post("/api/auth/register", json=request)

    assert response.status_code == status_code
    assert response.json()["code"] == error_code
    assert response.json()["retryable"] is False


def test_public_admin_registration_is_downgraded_to_user(tmp_path, monkeypatch):
    client = make_registration_client(tmp_path, monkeypatch)

    response = client.post(
        "/api/auth/register",
        json={
            "email": "self-promoted@example.test",
            "password": "Password123!",
            "role": "ADMIN",
        },
    )

    assert response.status_code == 200
    assert response.json()["user"]["role"] == "USER"
