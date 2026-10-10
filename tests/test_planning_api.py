from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.router import get_p_lite_pipeline
from app.main import create_app


def make_app(tmp_path: Path, monkeypatch, *, profile: str = "m1") -> FastAPI:
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", profile)
    monkeypatch.setenv("PROVIDER", "fake")
    return create_app(
        data_dir=tmp_path / "data",
        runs_dir=tmp_path / "runs",
    )


def authenticate(client: TestClient, email: str = "planning@example.test") -> None:
    response = client.post(
        "/api/auth/register",
        json={"email": email, "name": email, "password": "Password123!"},
    )
    assert response.status_code == 200


def test_decomposition_endpoint_returns_locked_result_from_callable_boundary(
    tmp_path: Path,
    monkeypatch,
) -> None:
    application = make_app(tmp_path, monkeypatch)
    calls: list[tuple[str, str | None]] = []

    async def fake_pipeline(request: str, provider: str | None = None):
        calls.append((request, provider))
        return {
            "request": request,
            "tasks": [
                {
                    "task_id": "T1",
                    "title": "Inspect the API contract",
                    "objective": "Check the request and response boundary.",
                    "expected_output": "A list of contract risks.",
                    "domain": "api_architecture",
                    "role_profile": "API reviewer",
                    "depends_on": [],
                }
            ],
            "planning_evidence_ids": ["plan-api-01"],
            "status": "SUCCEEDED",
            "warnings": [],
        }

    application.dependency_overrides[get_p_lite_pipeline] = lambda: fake_pipeline

    with TestClient(application) as client:
        authenticate(client)
        response = client.post(
            "/api/tasks/decompose",
            json={"request": "Review the API contract.", "provider": "fake"},
        )

    assert response.status_code == 200
    assert response.json()["request"] == "Review the API contract."
    assert response.json()["tasks"][0]["task_id"] == "T1"
    assert response.json()["planning_evidence_ids"] == ["plan-api-01"]
    assert calls == [("Review the API contract.", "fake")]


def test_decomposition_endpoint_preserves_existing_inspection_details(
    tmp_path: Path,
    monkeypatch,
) -> None:
    application = make_app(tmp_path, monkeypatch)

    async def fake_pipeline(request: str, _provider: str | None = None):
        return {
            "request": request,
            "tasks": [],
            "planning_evidence_ids": ["plan-api-01"],
            "status": "NO_EVIDENCE",
            "warnings": ["planning context is empty"],
            "planning": {
                "request": request,
                "item_ids": ["plan-api-01"],
                "scores": [0.75],
                "context": "Planning guidance only.",
                "snapshot_id": "planning_123",
                "selected_item_ids": ["plan-api-01"],
            },
            "planning_context": "Planning guidance only.",
            "latency_ms": 12,
            "llm_calls": 1,
            "metrics": {"latency_ms": 12, "llm_calls": 1},
        }

    application.dependency_overrides[get_p_lite_pipeline] = lambda: fake_pipeline

    with TestClient(application) as client:
        authenticate(client)
        response = client.post(
            "/api/tasks/decompose",
            json={"request": "Review the API contract."},
        )

    assert response.status_code == 200
    assert response.json()["planning"]["snapshot_id"] == "planning_123"
    assert response.json()["planning_context"] == "Planning guidance only."
    assert response.json()["latency_ms"] == 12
    assert response.json()["llm_calls"] == 1
    assert response.json()["metrics"] == {"latency_ms": 12, "llm_calls": 1}


def test_decomposition_endpoint_preserves_error_contract_for_blank_request(
    tmp_path: Path,
    monkeypatch,
) -> None:
    application = make_app(tmp_path, monkeypatch)

    async def fake_pipeline(_request: str, _provider: str | None = None):
        raise AssertionError("blank requests must be rejected before the pipeline")

    application.dependency_overrides[get_p_lite_pipeline] = lambda: fake_pipeline

    with TestClient(application) as client:
        authenticate(client)
        response = client.post("/api/tasks/decompose", json={"request": "  "})

    assert response.status_code == 400
    assert response.json() == {
        "detail": "request is required",
        "code": "REQUEST_REQUIRED",
        "message": "request is required",
        "retryable": False,
    }


def test_decomposition_endpoint_rejects_plite_in_m0_without_fallback(
    tmp_path: Path,
    monkeypatch,
) -> None:
    application = make_app(tmp_path, monkeypatch, profile="m0")
    calls: list[str] = []

    async def fake_pipeline(request: str, _provider: str | None = None):
        calls.append(request)
        return {}

    application.dependency_overrides[get_p_lite_pipeline] = lambda: fake_pipeline

    with TestClient(application) as client:
        authenticate(client)
        response = client.post(
            "/api/tasks/decompose",
            json={"request": "Review the API contract."},
        )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "P-lite is not available in profile m0",
        "code": "UNSUPPORTED_IMPLEMENTATION",
        "message": "P-lite is not available in profile m0",
        "retryable": False,
    }
    assert calls == []


def test_decomposition_endpoint_requires_authentication(tmp_path: Path, monkeypatch) -> None:
    application = make_app(tmp_path, monkeypatch)
    calls: list[str] = []

    async def fake_pipeline(request: str, _provider: str | None = None):
        calls.append(request)
        return {
            "request": request,
            "tasks": [
                {
                    "task_id": "T1",
                    "title": "Inspect the API contract",
                    "objective": "Check the request and response boundary.",
                    "expected_output": "A list of contract risks.",
                    "domain": "api_architecture",
                    "role_profile": "API reviewer",
                    "depends_on": [],
                }
            ],
            "planning_evidence_ids": ["plan-api-01"],
            "status": "SUCCEEDED",
            "warnings": [],
        }

    application.dependency_overrides[get_p_lite_pipeline] = lambda: fake_pipeline

    with TestClient(application) as client:
        anonymous = client.post(
            "/api/tasks/decompose", json={"request": "Review the API contract."}
        )
        assert anonymous.status_code == 401
        assert anonymous.json()["code"] == "AUTHENTICATION_REQUIRED"
        assert calls == []

        authenticate(client)
        authenticated = client.post(
            "/api/tasks/decompose", json={"request": "Review the API contract."}
        )

    assert authenticated.status_code == 200
    assert authenticated.json()["request"] == "Review the API contract."
    assert calls == ["Review the API contract."]


def test_runtime_exposes_p_lite_pipeline_without_changing_m0(
    tmp_path: Path,
    monkeypatch,
) -> None:
    application = make_app(tmp_path, monkeypatch)

    assert callable(application.state.api_runtime.p_lite_pipeline)

    with TestClient(application) as client:
        health = client.get("/api/health")

    assert health.status_code == 200
    assert health.json()["allowed_conditions"] == ["A", "B", "C"]
