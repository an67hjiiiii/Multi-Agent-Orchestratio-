from fastapi.testclient import TestClient

from app.auth.store import AuthStore
from app.main import app


def test_register_creates_persisted_user_without_exposing_secrets(tmp_path):
    store = AuthStore(tmp_path)
    app.state.auth_store = store

    with TestClient(app) as client:
        response = client.post(
            "/api/auth/register",
            json={
                "email": "student@example.test",
                "username": "student.one",
                "display_name": "Student One",
                "password": "correct-horse-battery",
            },
        )

    assert response.status_code == 201
    user = response.json()["user"]
    assert user["email"] == "student@example.test"
    assert user["role"] == "USER"
    assert "password" not in user
    assert "password_hash" not in user
    assert store.path.exists()


def test_register_rejects_duplicate_identity_and_role_escalation(tmp_path):
    app.state.auth_store = AuthStore(tmp_path)

    with TestClient(app) as client:
        first = client.post(
            "/api/auth/register",
            json={"email": "person@example.test", "password": "long-enough-password"},
        )
        duplicate = client.post(
            "/api/auth/register",
            json={"email": "PERSON@example.test", "password": "long-enough-password"},
        )
        role_escalation = client.post(
            "/api/auth/register",
            json={
                "email": "admin@example.test",
                "password": "long-enough-password",
                "role": "ADMIN",
            },
        )

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert role_escalation.status_code == 422
