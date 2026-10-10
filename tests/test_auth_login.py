from __future__ import annotations

import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


def make_client(tmp_path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "m0")
    monkeypatch.setenv("PROVIDER", "fake")
    monkeypatch.delenv("VECTOR_BACKEND", raising=False)
    monkeypatch.setenv("RETRIEVAL_MODE", "LEXICAL")
    monkeypatch.delenv("LOCAL_AUTH_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("LOCAL_AUTH_ADMIN_PASSWORD", raising=False)
    return TestClient(
        create_app(
            data_dir=tmp_path / "data",
            runs_dir=tmp_path / "runs",
            frontend_dist_dir=tmp_path / "missing-frontend",
        )
    )


def test_login_creates_hashed_session_and_restores_authenticated_user(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client(tmp_path, monkeypatch)
    credentials = {
        "email": "login@example.test",
        "username": "login.user",
        "password": "Password123!",
    }
    registered = client.post("/api/auth/register", json=credentials)
    assert registered.status_code == 200
    assert client.post("/api/auth/logout").status_code == 200

    response = client.post(
        "/api/auth/login",
        json={"identifier": "  LOGIN.USER  ", "password": credentials["password"]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["authenticated"] is True
    assert payload["user"]["email"] == credentials["email"]
    assert payload["user"]["role"] == "USER"
    assert payload["user"]["last_login_at"]
    assert payload["session"]["user_id"] == payload["user"]["user_id"]
    assert payload["access_token"] == payload["token"]
    assert "session_token=" in response.headers["set-cookie"]
    assert "httponly" in response.headers["set-cookie"].lower()

    restored = client.get("/api/auth/session").json()
    assert restored["authenticated"] is True
    assert restored["user"]["user_id"] == payload["user"]["user_id"]

    stored_auth = json.loads((tmp_path / "data" / "auth.json").read_text(encoding="utf-8"))
    raw_token = payload["access_token"]
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    assert any(session["token_hash"] == token_hash for session in stored_auth["sessions"])
    serialized_store = json.dumps(stored_auth)
    assert raw_token not in serialized_store
    assert credentials["password"] not in serialized_store


def test_login_allows_only_server_bootstrapped_admin_credentials(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "m0")
    monkeypatch.setenv("PROVIDER", "fake")
    monkeypatch.delenv("VECTOR_BACKEND", raising=False)
    monkeypatch.setenv("RETRIEVAL_MODE", "LEXICAL")
    monkeypatch.setenv("LOCAL_AUTH_ADMIN_EMAIL", "local-admin@example.test")
    monkeypatch.setenv("LOCAL_AUTH_ADMIN_PASSWORD", "AdminPassword123!")
    client = TestClient(
        create_app(
            data_dir=tmp_path / "data",
            runs_dir=tmp_path / "runs",
            frontend_dist_dir=tmp_path / "missing-frontend",
        )
    )

    response = client.post(
        "/api/auth/login",
        json={"email": "local-admin@example.test", "password": "AdminPassword123!"},
    )

    assert response.status_code == 200
    assert response.json()["user"]["role"] == "ADMIN"
    assert response.json()["authenticated"] is True


def test_login_returns_stable_generic_errors(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = make_client(tmp_path, monkeypatch)
    registration = client.post(
        "/api/auth/register",
        json={"email": "login-errors@example.test", "password": "Password123!"},
    )
    assert registration.status_code == 200
    assert client.post("/api/auth/logout").status_code == 200

    wrong_password = client.post(
        "/api/auth/login",
        json={"email": "login-errors@example.test", "password": "WrongPassword!"},
    )
    unknown_user = client.post(
        "/api/auth/login",
        json={"email": "unknown@example.test", "password": "WrongPassword!"},
    )
    missing_identifier = client.post(
        "/api/auth/login",
        json={"password": "Password123!"},
    )

    assert wrong_password.status_code == unknown_user.status_code == 401
    assert wrong_password.json()["code"] == unknown_user.json()["code"] == "INVALID_CREDENTIALS"
    assert wrong_password.json()["message"] == unknown_user.json()["message"]
    assert missing_identifier.status_code == 400
    assert missing_identifier.json()["code"] == "IDENTIFIER_REQUIRED"
    assert "set-cookie" not in wrong_password.headers
    assert "set-cookie" not in unknown_user.headers
    assert "set-cookie" not in missing_identifier.headers

    session = client.get("/api/auth/session")
    assert session.status_code == 200
    assert session.json()["authenticated"] is False
    assert session.json()["user"] is None
    assert client.get("/api/auth/me").status_code == 401
