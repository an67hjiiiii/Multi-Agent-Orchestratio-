from __future__ import annotations

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

    response = client.post("/api/auth/logout")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "authenticated": False}
    cleared_cookies = [header.lower() for header in response.headers.get_list("set-cookie")]
    for cookie_name in ("session_token=", "local_session="):
        assert any(cookie_name in header and "max-age=0" in header for header in cleared_cookies)

    session = client.get("/api/auth/session")
    assert session.status_code == 200
    assert session.json()["authenticated"] is False
    assert session.json()["user"] is None

    revoked_session = client.get(
        "/api/auth/session",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert revoked_session.status_code == 200
    assert revoked_session.json()["authenticated"] is False

    protected = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert protected.status_code == 401
    assert protected.json()["code"] == "AUTHENTICATION_REQUIRED"

    repeated_logout = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
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
