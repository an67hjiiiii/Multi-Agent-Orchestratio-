from fastapi.testclient import TestClient

from app.main import create_app


def test_logout_revokes_only_the_calling_users_session(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "m0")
    monkeypatch.setenv("PROVIDER", "fake")
    monkeypatch.setenv("RETRIEVAL_MODE", "LEXICAL")
    monkeypatch.delenv("VECTOR_BACKEND", raising=False)
    monkeypatch.delenv("LOCAL_AUTH_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("LOCAL_AUTH_ADMIN_PASSWORD", raising=False)

    app = create_app(
        data_dir=tmp_path / "data",
        runs_dir=tmp_path / "runs",
        frontend_dist_dir=tmp_path / "missing-frontend",
    )
    first_user = TestClient(app)
    second_user = TestClient(app)

    first_registration = first_user.post(
        "/api/auth/register",
        json={"email": "first@example.test", "password": "Password123!"},
    )
    second_registration = second_user.post(
        "/api/auth/register",
        json={"email": "second@example.test", "password": "Password123!"},
    )

    assert first_registration.status_code == second_registration.status_code == 200
    first_token = first_registration.json()["access_token"]
    second_token = second_registration.json()["access_token"]
    first_bearer = {"Authorization": f"Bearer {first_token}"}
    second_bearer = {"Authorization": f"Bearer {second_token}"}
    first_user_id = first_registration.json()["user"]["user_id"]
    second_user_id = second_registration.json()["user"]["user_id"]
    assert first_user_id != second_user_id

    first_session = first_user.get("/api/auth/session").json()
    second_session = second_user.get("/api/auth/session").json()
    assert first_session["authenticated"] is True
    assert first_session["user"]["user_id"] == first_user_id
    assert second_session["authenticated"] is True
    assert second_session["user"]["user_id"] == second_user_id
    assert first_user.get("/api/auth/me", headers=first_bearer).status_code == 200
    assert second_user.get("/api/auth/me", headers=second_bearer).status_code == 200

    logout = first_user.post("/api/auth/logout")

    assert logout.status_code == 200
    assert logout.json() == {"ok": True, "authenticated": False}
    first_session_after_logout = first_user.get("/api/auth/session").json()
    assert first_session_after_logout["authenticated"] is False
    assert first_session_after_logout["user"] is None
    assert first_user.get("/api/auth/me").status_code == 401
    assert first_user.get("/api/auth/me", headers=first_bearer).status_code == 401

    second_session_after_logout = second_user.get("/api/auth/session").json()
    assert second_session_after_logout["authenticated"] is True
    assert second_session_after_logout["user"]["user_id"] == second_user_id
    second_current_user = second_user.get("/api/auth/me")
    assert second_current_user.status_code == 200
    assert second_current_user.json()["user"]["user_id"] == second_user_id
    second_bearer_user = second_user.get("/api/auth/me", headers=second_bearer)
    assert second_bearer_user.status_code == 200
    assert second_bearer_user.json()["user"]["user_id"] == second_user_id
