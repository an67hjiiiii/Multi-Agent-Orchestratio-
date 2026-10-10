import pytest
from fastapi.testclient import TestClient

from app.auth.store import AuthStore, InvalidSessionError
from app.main import app


def test_logout_revokes_cookie_session_and_clears_cookie(tmp_path):
    store = AuthStore(tmp_path)
    user = store.register(email="logout@example.test", password="correct-horse-battery")
    token, _session = store.create_session(user["user_id"])
    app.state.auth_store = store

    with TestClient(app) as client:
        client.cookies.set("session_token", token)
        response = client.post("/api/auth/logout")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "authenticated": False}
    assert "session_token=\"\"" in response.headers["set-cookie"]
    with pytest.raises(InvalidSessionError):
        store.resolve(token)


def test_logout_is_safe_without_a_session(tmp_path):
    app.state.auth_store = AuthStore(tmp_path)

    with TestClient(app) as client:
        response = client.post("/api/auth/logout")

    assert response.status_code == 200
    assert response.json()["authenticated"] is False
