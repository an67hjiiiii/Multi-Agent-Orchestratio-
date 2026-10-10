from fastapi.testclient import TestClient

from app.auth.store import AuthStore
from app.main import app


def test_login_returns_session_and_http_only_cookie(tmp_path):
    store = AuthStore(tmp_path)
    store.register(
        email="login@example.test",
        password="correct-horse-battery",
    )
    app.state.auth_store = store

    with TestClient(app) as client:
        response = client.post(
            "/api/auth/login",
            json={"email": " LOGIN@example.test ", "password": "correct-horse-battery"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["authenticated"] is True
    assert payload["user"]["email"] == "login@example.test"
    assert payload["session"]["user_id"] == payload["user"]["user_id"]
    assert payload["access_token"] == payload["token"]
    assert "password_hash" not in payload["user"]
    cookie = response.headers["set-cookie"].lower()
    assert "session_token=" in cookie
    assert "httponly" in cookie
    assert "samesite=lax" in cookie


def test_login_rejects_invalid_credentials_without_session(tmp_path):
    store = AuthStore(tmp_path)
    store.register(email="login@example.test", password="correct-horse-battery")
    app.state.auth_store = store

    with TestClient(app) as client:
        response = client.post(
            "/api/auth/login",
            json={"identifier": "login@example.test", "password": "wrong-password"},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email, username, or password"
    assert "set-cookie" not in response.headers
