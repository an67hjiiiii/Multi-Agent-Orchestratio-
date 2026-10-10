from fastapi.testclient import TestClient

from app.auth.store import AuthStore
from app.main import app


def test_current_session_resolves_bearer_token(tmp_path):
    store = AuthStore(tmp_path)
    user = store.register(email="session@example.test", password="correct-horse-battery")
    token, _session = store.create_session(user["user_id"])
    app.state.auth_store = store

    with TestClient(app) as client:
        response = client.get(
            "/api/auth/session",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert response.json() == {"authenticated": True, "user": user}


def test_current_session_rejects_missing_or_revoked_token(tmp_path):
    store = AuthStore(tmp_path)
    user = store.register(email="session@example.test", password="correct-horse-battery")
    token, _session = store.create_session(user["user_id"])
    app.state.auth_store = store

    with TestClient(app) as client:
        missing = client.get("/api/auth/session")
        client.cookies.set("session_token", token)
        store.revoke(token)
        revoked = client.get("/api/auth/session")

    assert missing.status_code == 401
    assert revoked.status_code == 401
