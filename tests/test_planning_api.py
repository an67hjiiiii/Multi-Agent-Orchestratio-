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
        response = client.post(
            "/api/tasks/decompose",
            json={"request": "Review the API contract.", "provider": "fake"},
        )

    assert response.status_code == 200
    assert response.json()["request"] == "Review the API contract."
    assert response.json()["tasks"][0]["task_id"] == "T1"
    assert response.json()["planning_evidence_ids"] == ["plan-api-01"]
    assert calls == [("Review the API contract.", "fake")]


def test_decomposition_endpoint_preserves_error_contract_for_blank_request(
    tmp_path: Path,
    monkeypatch,
) -> None:
    application = make_app(tmp_path, monkeypatch)

    async def fake_pipeline(_request: str, _provider: str | None = None):
        raise AssertionError("blank requests must be rejected before the pipeline")

    application.dependency_overrides[get_p_lite_pipeline] = lambda: fake_pipeline

    with TestClient(application) as client:
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


def test_decomposition_endpoint_reports_missing_pipeline_without_m0_changes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    application = make_app(tmp_path, monkeypatch)

    with TestClient(application) as client:
        response = client.post(
            "/api/tasks/decompose",
            json={"request": "Review the API contract."},
        )
        health = client.get("/api/health")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "P-lite pipeline is unavailable",
        "code": "PLITE_UNAVAILABLE",
        "message": "P-lite pipeline is unavailable",
        "retryable": True,
    }
    assert health.status_code == 200
    assert health.json()["allowed_conditions"] == ["A", "B", "C"]
