from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def make_frontend_dist(tmp_path: Path) -> Path:
    dist = tmp_path / "frontend" / "dist"
    assets = dist / "assets"
    assets.mkdir(parents=True)
    (dist / "index.html").write_text(
        """<!doctype html>
<html><head><title>Local Multi-Agent RAG modern React</title></head>
<body><div id=\"root\"></div><script type=\"module\" src=\"/assets/app.js\"></script></body></html>
""",
        encoding="utf-8",
    )
    (assets / "app.js").write_text("console.log('modern frontend');\n", encoding="utf-8")
    return dist


def make_client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "m0")
    monkeypatch.setenv("PROVIDER", "fake")
    monkeypatch.delenv("VECTOR_BACKEND", raising=False)
    client = TestClient(
        create_app(
            data_dir=tmp_path / "data",
            runs_dir=tmp_path / "runs",
            frontend_dist_dir=make_frontend_dist(tmp_path),
        )
    )
    registered = client.post(
        "/api/auth/register",
        json={"email": "api@example.test", "name": "API", "password": "Password123!"},
    )
    assert registered.status_code == 200
    return client


def test_api_boundary_preserves_static_frontend_and_m0_health(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)

    root = client.get("/")
    assert root.status_code == 200
    assert "Local Multi-Agent RAG" in root.text
    assert 'id="root"' in root.text

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["allowed_conditions"] == ["A"]
    assert health.json()["implementation_profile"] == "m0"

    kb_status = client.get("/api/kb/status")
    assert kb_status.status_code == 200
    assert kb_status.json() == {
        "status": "EMPTY",
        "backend": "local_json",
        "retrieval_backend": "lexical",
        "embedding_version": None,
        "vector_indexed_chunks": 0,
        "index_identity": None,
        "index_status": "NOT_CONFIGURED",
        "source_count": 0,
        "chunk_count": 0,
        "snapshot_id": kb_status.json()["snapshot_id"],
    }


def test_api_boundary_serves_vite_assets_spa_fallback_and_keeps_legacy_explicit(
    tmp_path,
    monkeypatch,
):
    client = make_client(tmp_path, monkeypatch)

    asset = client.get("/assets/app.js")
    assert asset.status_code == 200
    assert "modern frontend" in asset.text

    root = client.get("/")
    nested = client.get("/workspace/runs/example")
    assert nested.status_code == 200
    assert nested.text == root.text

    legacy = client.get("/static/index.html")
    assert legacy.status_code == 200
    assert "Research Chat" in legacy.text
    assert legacy.text != root.text

    unknown_api = client.get("/api/not-a-real-route")
    assert unknown_api.status_code == 404
    assert unknown_api.json() == {
        "detail": "API route not found",
        "code": "NOT_FOUND",
        "message": "API route not found",
        "retryable": False,
    }


def test_api_boundary_does_not_use_legacy_shell_when_frontend_build_is_missing(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "m0")
    monkeypatch.setenv("PROVIDER", "fake")
    client = TestClient(
        create_app(
            data_dir=tmp_path / "data",
            runs_dir=tmp_path / "runs",
            frontend_dist_dir=tmp_path / "missing-dist",
        )
    )

    root = client.get("/")
    assert root.status_code == 503
    assert "Frontend build is unavailable" in root.text

    legacy = client.get("/static/index.html")
    assert legacy.status_code == 200
    assert "Research Chat" in legacy.text


def test_api_boundary_imports_sources_and_runs_m0_chat(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)

    imported = client.post(
        "/api/sources/text",
        json={
            "source_name": "api.md",
            "text": "The API contract defines request validation and error responses.",
        },
    )
    assert imported.status_code == 200
    assert imported.json()["chunks_added"] == 1

    source_id = imported.json()["source_id"]
    source = client.get(f"/api/sources/{source_id}")
    assert source.status_code == 200
    assert source.json()["chunks"][0]["text"] == (
        "The API contract defines request validation and error responses."
    )
    chunk_id = source.json()["chunks"][0]["chunk_id"]
    chunk = client.get(f"/api/chunks/{chunk_id}")
    assert chunk.status_code == 200
    assert chunk.json()["source_id"] == source_id

    kb_status = client.get("/api/kb/status")
    assert kb_status.status_code == 200
    assert kb_status.json()["status"] == "READY"
    assert kb_status.json()["retrieval_backend"] == "lexical"
    assert kb_status.json()["source_count"] == 1
    assert kb_status.json()["chunk_count"] == 1

    run_response = client.post(
        "/api/chat",
        json={"message": "What does the API contract define?", "condition": "A", "provider": "fake"},
    )
    assert run_response.status_code == 200
    run = run_response.json()
    assert run["status"] == "COMPLETE"
    assert run["condition"] == "A"
    assert client.get(f"/api/runs/{run['run_id']}").json()["run_id"] == run["run_id"]
    assert client.get("/api/runs").json()[0]["run_id"] == run["run_id"]


def test_api_boundary_keeps_validation_errors_explicit(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)

    blank_chat = client.post("/api/chat", json={"message": "   "})
    assert blank_chat.status_code == 400
    assert blank_chat.json()["detail"] == "message is required"
    assert blank_chat.json()["code"] == "MESSAGE_REQUIRED"
    assert blank_chat.json()["message"] == "message is required"
    assert blank_chat.json()["retryable"] is False

    unsupported_condition = client.post(
        "/api/chat",
        json={"message": "anything", "condition": "B", "provider": "fake"},
    )
    assert unsupported_condition.status_code == 400
    assert "not available in profile m0" in unsupported_condition.json()["detail"]
    assert unsupported_condition.json()["code"] == "UNSUPPORTED_CONDITION"

    missing_source = client.get("/api/sources/not-found")
    assert missing_source.status_code == 404
    assert missing_source.json()["detail"] == "source not found"
    assert missing_source.json()["code"] == "NOT_FOUND"


def test_api_boundary_rejects_empty_source_name_and_payload_validation(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)

    empty_name = client.post(
        "/api/sources/text",
        json={"source_name": "   ", "text": "content"},
    )
    assert empty_name.status_code == 400
    assert empty_name.json() == {
        "detail": "source_name is required",
        "code": "SOURCE_NAME_REQUIRED",
        "message": "source_name is required",
        "retryable": False,
    }

    missing_body_field = client.post("/api/chat", json={})
    assert missing_body_field.status_code == 422
    assert missing_body_field.json()["code"] == "VALIDATION_ERROR"
    assert missing_body_field.json()["message"] == "Request validation failed"
    assert missing_body_field.json()["retryable"] is False
    assert isinstance(missing_body_field.json()["detail"], list)


def test_api_boundary_keeps_config_errors_safe_and_stable(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)

    config = client.get("/api/config")
    assert config.status_code == 200
    assert config.json()["allowed_conditions"] == ["A"]
    assert config.json()["config_hash"]

    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "invalid-profile")
    invalid = client.get("/api/config")
    assert invalid.status_code == 500
    assert invalid.json() == {
        "detail": "Runtime configuration is invalid",
        "code": "INVALID_CONFIGURATION",
        "message": "Runtime configuration is invalid",
        "retryable": False,
    }


def test_api_boundary_sanitizes_local_model_health_failures(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)

    async def fail_health(self):
        raise RuntimeError("provider body contains a secret-looking detail")

    monkeypatch.setattr("app.api.router.OllamaProvider.health", fail_health)
    response = client.get("/api/local-model/health")

    assert response.status_code == 200
    assert response.json() == {
        "ok": False,
        "error": "Local Ollama health check failed",
        "code": "LOCAL_MODEL_UNAVAILABLE",
        "message": "Local Ollama health check failed",
        "retryable": True,
        "configured_model": "qwen3:4b",
    }


def test_api_boundary_accepts_utf8_file_upload(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)

    response = client.post(
        "/api/sources/file",
        files={"file": ("notes.md", "Nội dung có dấu.", "text/markdown")},
    )
    assert response.status_code == 200
    assert response.json()["source_name"] == "notes.md"


def test_api_boundary_delegates_to_optional_knowledge_base_service(tmp_path, monkeypatch):
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "m0")
    monkeypatch.setenv("PROVIDER", "fake")
    application = create_app(
        data_dir=tmp_path / "data",
        runs_dir=tmp_path / "runs",
        frontend_dist_dir=make_frontend_dist(tmp_path),
    )
    owner_user_id = ""

    class StubKnowledgeBase:
        def status(self):
            return {
                "schema_version": "knowledge-v2",
                "retrieval_backend": "qdrant",
                "embedding_version": "local-embed-v1",
                "vector_indexed_chunks": 1,
                "source_count": 1,
                "chunk_count": 1,
                "snapshot_id": "corpus_vector",
            }

        def list_sources(self):
            return [{
                "source_id": "src_vector",
                "source_name": "notes.md",
                "chunk_count": 1,
                "provenance": {"owner_user_id": owner_user_id},
            }]

        def source(self, source_id):
            return {
                "source_id": source_id,
                "source_name": "notes.md",
                "provenance": {"owner_user_id": owner_user_id},
                "chunks": [self.chunk("chunk_vector")],
            }

        def chunk(self, chunk_id):
            return {
                "chunk_id": chunk_id,
                "source_id": "src_vector",
                "source_name": "notes.md",
                "text": "Vector-backed evidence",
                "index": 0,
                "score": 0.9,
                "provenance": {"origin": "upload", "owner_user_id": owner_user_id},
            }

        def import_text(self, source_name, text, *, provenance):
            assert provenance["origin"] == "api_text"
            assert provenance["owner_user_id"] == owner_user_id
            return {
                "source_id": "src_vector",
                "source_name": source_name,
                "chunks_added": 1,
                "total_chunks_for_source": 1,
                "snapshot_id": "corpus_vector",
                "retrieval_backend": "qdrant",
                "vector_indexed_chunks": 1,
            }

        def import_document(self, source_name, data, *, origin, content_type, provenance):
            assert source_name == "upload.md"
            assert data == b"Uploaded evidence"
            assert origin == "upload"
            assert content_type == "text/markdown"
            assert provenance["owner_user_id"] == owner_user_id
            return {
                "source_id": "src_vector",
                "source_name": source_name,
                "chunks_added": 1,
                "total_chunks_for_source": 1,
                "snapshot_id": "corpus_vector",
                "retrieval_backend": "qdrant",
                "vector_indexed_chunks": 1,
            }

    application.state.api_runtime.knowledge_base = StubKnowledgeBase()
    client = TestClient(application)
    registered = client.post(
        "/api/auth/register",
        json={"email": "vector@example.test", "name": "Vector", "password": "Password123!"},
    )
    assert registered.status_code == 200
    owner_user_id = registered.json()["user"]["user_id"]

    status = client.get("/api/kb/status").json()
    assert status["status"] == "READY"
    assert status["backend"] == "qdrant"
    assert status["index_status"] == "READY"
    assert client.get("/api/sources").json()["sources"][0]["source_id"] == "src_vector"
    imported = client.post(
        "/api/sources/text",
        json={"source_name": "notes.md", "text": "Vector-backed evidence"},
    )
    assert imported.status_code == 200
    uploaded = client.post(
        "/api/sources/file",
        files={"file": ("upload.md", "Uploaded evidence", "text/markdown")},
    )
    assert uploaded.status_code == 200
    assert uploaded.json()["retrieval_backend"] == "qdrant"
    assert client.get("/api/sources/src_vector").json()["source_name"] == "notes.md"
    assert client.get("/api/chunks/chunk_vector").json()["provenance"] == {
        "origin": "upload",
        "owner_user_id": owner_user_id,
    }


def test_api_boundary_does_not_silently_fallback_when_vector_backend_is_explicit(
    tmp_path,
    monkeypatch,
):
    client = make_client(tmp_path, monkeypatch)
    monkeypatch.setenv("VECTOR_BACKEND", "qdrant")

    response = client.get("/api/kb/status")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Configured vector knowledge base is unavailable",
        "code": "KNOWLEDGE_BASE_UNAVAILABLE",
        "message": "Configured vector knowledge base is unavailable",
        "retryable": True,
    }

    chat = client.post(
        "/api/chat",
        json={"message": "use the configured corpus", "condition": "A", "provider": "fake"},
    )
    assert chat.status_code == 503
    assert chat.json()["code"] == "KNOWLEDGE_BASE_UNAVAILABLE"
