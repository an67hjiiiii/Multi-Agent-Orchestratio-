from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.storage.source_store import SourceStore


def register(client: TestClient, email: str) -> None:
    response = client.post(
        "/api/auth/register",
        json={"email": email, "name": email, "password": "Password123!"},
    )
    assert response.status_code == 200


def test_source_reads_are_scoped_to_the_importing_local_user(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "m0")
    monkeypatch.setenv("PROVIDER", "fake")
    application = create_app(data_dir=tmp_path / "data", runs_dir=tmp_path / "runs")
    owner = TestClient(application)
    other_user = TestClient(application)
    register(owner, "owner@example.test")
    register(other_user, "other@example.test")

    imported = owner.post(
        "/api/sources/text",
        json={"source_name": "private.md", "text": "Only the owner may inspect this source."},
    )
    assert imported.status_code == 200
    source_id = imported.json()["source_id"]
    owner_source = owner.get(f"/api/sources/{source_id}")
    chunk_id = owner_source.json()["chunks"][0]["chunk_id"]

    assert owner_source.status_code == 200
    assert owner.get("/api/sources").json()["sources"][0]["source_id"] == source_id
    assert owner.get(f"/api/chunks/{chunk_id}").status_code == 200
    assert other_user.get(f"/api/sources/{source_id}").status_code == 404
    assert other_user.get(f"/api/chunks/{chunk_id}").status_code == 404
    assert other_user.get("/api/sources").json()["sources"] == []


def test_file_upload_is_authenticated_owner_scoped_and_failure_does_not_persist(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "m0")
    monkeypatch.setenv("PROVIDER", "fake")
    monkeypatch.setenv("RETRIEVAL_MODE", "LEXICAL")
    monkeypatch.delenv("VECTOR_BACKEND", raising=False)
    application = create_app(data_dir=tmp_path / "data", runs_dir=tmp_path / "runs")
    owner = TestClient(application)
    other_user = TestClient(application)
    anonymous = TestClient(application)

    owner_registration = owner.post(
        "/api/auth/register",
        json={
            "email": "upload-owner@example.test",
            "name": "Upload owner",
            "password": "Password123!",
        },
    )
    assert owner_registration.status_code == 200
    register(other_user, "upload-other@example.test")

    anonymous_upload = anonymous.post(
        "/api/sources/file",
        files={"file": ("private.txt", b"Private uploaded evidence.", "text/plain")},
    )
    assert anonymous_upload.status_code == 401
    assert owner.get("/api/sources").json()["sources"] == []

    uploaded = owner.post(
        "/api/sources/file",
        files={"file": ("private.txt", b"Private uploaded evidence.", "text/plain")},
    )
    assert uploaded.status_code == 200
    source_id = uploaded.json()["source_id"]
    owner_user_id = owner_registration.json()["user"]["user_id"]
    owner_source = owner.get(f"/api/sources/{source_id}")
    assert owner_source.status_code == 200
    assert owner_source.json()["provenance"]["owner_user_id"] == owner_user_id
    chunk_id = owner_source.json()["chunks"][0]["chunk_id"]
    assert owner.get(f"/api/chunks/{chunk_id}").status_code == 200
    assert other_user.get(f"/api/sources/{source_id}").status_code == 404
    assert other_user.get(f"/api/chunks/{chunk_id}").status_code == 404

    rejected = owner.post(
        "/api/sources/file",
        files={"file": ("payload.exe", b"not a supported document", "application/octet-stream")},
    )
    assert rejected.status_code == 415
    assert rejected.json()["code"] == "UNSUPPORTED_DOCUMENT_TYPE"
    assert [item["source_id"] for item in owner.get("/api/sources").json()["sources"]] == [source_id]


@pytest.mark.parametrize("retrieval_mode", ["LEXICAL", "VECTOR", "HYBRID"])
def test_kb_search_is_authenticated_and_owner_scoped(tmp_path: Path, monkeypatch, retrieval_mode: str) -> None:
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "m0")
    monkeypatch.setenv("PROVIDER", "fake")
    monkeypatch.setenv("RETRIEVAL_MODE", retrieval_mode)
    if retrieval_mode == "LEXICAL":
        monkeypatch.delenv("VECTOR_BACKEND", raising=False)
    else:
        monkeypatch.setenv("VECTOR_BACKEND", "memory")
    application = create_app(data_dir=tmp_path / "data", runs_dir=tmp_path / "runs")
    owner = TestClient(application)
    other_user = TestClient(application)
    anonymous = TestClient(application)
    register(owner, "search-owner@example.test")
    register(other_user, "search-other@example.test")

    first = owner.post(
        "/api/sources/text",
        json={"source_name": "owner.md", "text": "Zephyrquartz belongs only to the first owner."},
    )
    second = other_user.post(
        "/api/sources/text",
        json={
            "source_name": "other.md",
            "text": "Zephyrquartz belongs only to the second owner.",
        },
    )
    assert first.status_code == second.status_code == 200
    query = {"query": "Zephyrquartz", "top_k": 10}

    assert anonymous.get("/api/kb/search", params=query).status_code == 401
    owned = owner.get("/api/kb/search", params=query)
    assert owned.status_code == 200
    owner_results = owned.json()["results"]
    assert owner_results
    assert all(item["source_id"] == first.json()["source_id"] for item in owner_results)
    foreign = other_user.get("/api/kb/search", params=query)
    assert foreign.status_code == 200
    other_results = foreign.json()["results"]
    assert other_results
    assert all(item["source_id"] == second.json()["source_id"] for item in other_results)

    for results, source in (
        (owner_results, first.json()),
        (other_results, second.json()),
    ):
        for item in results:
            assert item["chunk_id"]
            assert item["source_id"] == source["source_id"]
            assert item["provenance"]["source_id"] == item["source_id"]
            assert item["provenance"]["chunk_id"] == item["chunk_id"]
            assert (
                item["provenance"]["owner_user_id"]
                == source["provenance"]["owner_user_id"]
            )


def test_identical_imports_keep_private_source_and_chunk_provenance(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "m0")
    monkeypatch.setenv("PROVIDER", "fake")
    application = create_app(data_dir=tmp_path / "data", runs_dir=tmp_path / "runs")
    first_user = TestClient(application)
    second_user = TestClient(application)
    register(first_user, "duplicate-first@example.test")
    register(second_user, "duplicate-second@example.test")
    body = {"source_name": "same.md", "text": "The same private content can belong to different users."}

    first = first_user.post("/api/sources/text", json=body)
    first_repeat = first_user.post("/api/sources/text", json=body)
    second = second_user.post("/api/sources/text", json=body)
    second_repeat = second_user.post("/api/sources/text", json=body)
    assert all(response.status_code == 200 for response in (first, first_repeat, second, second_repeat))
    first_id = first.json()["source_id"]
    second_id = second.json()["source_id"]
    assert first_id != second_id
    assert first_repeat.json()["source_id"] == first_id
    assert second_repeat.json()["source_id"] == second_id
    assert first_repeat.json()["chunks_added"] == second_repeat.json()["chunks_added"] == 0

    first_source = first_user.get(f"/api/sources/{first_id}")
    second_source = second_user.get(f"/api/sources/{second_id}")
    assert first_source.status_code == second_source.status_code == 200
    first_chunk = first_source.json()["chunks"][0]
    second_chunk = second_source.json()["chunks"][0]
    assert first_chunk["chunk_id"] != second_chunk["chunk_id"]
    assert first_chunk["provenance"]["owner_user_id"] == first_source.json()["provenance"]["owner_user_id"]
    assert second_chunk["provenance"]["owner_user_id"] == second_source.json()["provenance"]["owner_user_id"]
    assert first_user.get(f"/api/sources/{second_id}").status_code == 404
    assert second_user.get(f"/api/sources/{first_id}").status_code == 404
    assert first_user.get(f"/api/chunks/{second_chunk['chunk_id']}").status_code == 404
    assert second_user.get(f"/api/chunks/{first_chunk['chunk_id']}").status_code == 404

    reopened = SourceStore(tmp_path / "data")
    assert reopened.source(first_id)["provenance"]["owner_user_id"] == first_chunk["provenance"]["owner_user_id"]
    assert reopened.source(second_id)["provenance"]["owner_user_id"] == second_chunk["provenance"]["owner_user_id"]
