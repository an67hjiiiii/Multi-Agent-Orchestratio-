from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.storage.run_store import RunStore


def test_run_lookup_cannot_escape_run_root(tmp_path):
    outside = tmp_path / "private.json"
    outside.write_text(json.dumps({"marker": "outside"}), encoding="utf-8")
    store = RunStore(str(tmp_path / "runs"))

    assert store.get(r"..\private") is None

    client = TestClient(create_app(data_dir=tmp_path / "data", runs_dir=tmp_path / "runs"))
    registered = client.post(
        "/api/auth/register",
        json={"email": "run-security@example.test", "name": "Run security", "password": "Password123!"},
    )
    assert registered.status_code == 200
    response = client.get("/api/runs/..%5Cprivate")
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_run_save_rejects_path_like_identifier(tmp_path):
    store = RunStore(str(tmp_path / "runs"))

    with pytest.raises(ValueError, match="run_id"):
        store.save({"run_id": r"..\private"})
    assert not (tmp_path / "private.json").exists()
