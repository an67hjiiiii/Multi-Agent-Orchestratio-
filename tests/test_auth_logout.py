from __future__ import annotations

from http.cookies import SimpleCookie

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


def test_logout_revokes_session_clears_cookies_and_is_idempotent(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client(tmp_path, monkeypatch)
    registered = client.post(
        "/api/auth/register",
        json={"email": "logout@example.test", "password": "Password123!"},
    )
    assert registered.status_code == 200
    token = registered.json()["access_token"]
    client.cookies.clear()

    bearer_headers = {"Authorization": f"Bearer {token}"}
    authenticated_session = client.get("/api/auth/session", headers=bearer_headers)
    assert authenticated_session.status_code == 200
    assert authenticated_session.json()["authenticated"] is True
    authorized_user = client.get("/api/auth/me", headers=bearer_headers)
    assert authorized_user.status_code == 200
    assert authorized_user.json()["authenticated"] is True

    response = client.post("/api/auth/logout", headers=bearer_headers)

    assert response.status_code == 200
    assert response.json() == {"ok": True, "authenticated": False}
    cleared_cookies = {}
    for header in response.headers.get_list("set-cookie"):
        parsed_cookie = SimpleCookie()
        parsed_cookie.load(header)
        cleared_cookies.update(parsed_cookie)
    for cookie_name in ("session_token", "local_session"):
        assert cookie_name in cleared_cookies
        assert cleared_cookies[cookie_name]["max-age"] == "0"

    session = client.get("/api/auth/session")
    assert session.status_code == 200
    assert session.json()["authenticated"] is False
    assert session.json()["user"] is None

    revoked_session = client.get(
        "/api/auth/session",
        headers=bearer_headers,
    )
    assert revoked_session.status_code == 200
    assert revoked_session.json()["authenticated"] is False

    protected = client.get(
        "/api/auth/me",
        headers=bearer_headers,
    )
    assert protected.status_code == 401
    assert protected.json()["code"] == "AUTHENTICATION_REQUIRED"

    repeated_logout = client.post(
        "/api/auth/logout",
        headers=bearer_headers,
    )
    assert repeated_logout.status_code == 200
    assert repeated_logout.json() == {"ok": True, "authenticated": False}


def test_logout_without_session_still_returns_signed_out_state(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client(tmp_path, monkeypatch)

    first = client.post("/api/auth/logout")
    second = client.post("/api/auth/logout")

    assert first.status_code == 200
    assert first.json() == {"ok": True, "authenticated": False}
    assert second.status_code == 200
    assert second.json() == first.json()
