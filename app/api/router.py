from __future__ import annotations

import os

from fastapi import APIRouter, Depends, File, UploadFile

from app.api.dependencies import get_api_runtime
from app.api.errors import ApiError
from app.api.schemas import ChatRequest, SourceTextRequest
from app.core.api_runtime import ApiRuntime
from app.core.config import RuntimeConfig
from app.providers.ollama import OllamaProvider


router = APIRouter(prefix="/api")
MAX_SOURCE_BYTES = 2_000_000


def _runtime_config() -> RuntimeConfig:
    try:
        return RuntimeConfig.from_env()
    except (TypeError, ValueError, OverflowError) as exc:
        raise ApiError(
            500,
            "INVALID_CONFIGURATION",
            "Runtime configuration is invalid",
        ) from exc


def _pipeline_value_error(exc: ValueError) -> ApiError:
    detail = str(exc)
    if detail.startswith("Condition "):
        code = "UNSUPPORTED_CONDITION"
    elif detail.startswith("Unknown condition"):
        code = "INVALID_CONDITION"
    elif detail.startswith("Only fake and local Ollama providers"):
        code = "UNSUPPORTED_PROVIDER"
    else:
        code = "INVALID_REQUEST"
    return ApiError(400, code, detail or "Request could not be processed")


@router.get("/health")
def health(runtime: ApiRuntime = Depends(get_api_runtime)):
    cfg = _runtime_config()
    return {
        "ok": True,
        "app": "local-multi-agent-rag",
        "version": "0.2.0-m0",
        "implementation_profile": cfg.implementation_profile,
        "allowed_conditions": cfg.allowed_conditions(),
        "default_provider": cfg.provider,
        "source_snapshot_id": runtime.source_store.snapshot_id(),
        "config_hash": cfg.config_hash(),
    }


@router.get("/config")
def config():
    cfg = _runtime_config()
    return {
        **cfg.public_dict(),
        "allowed_conditions": cfg.allowed_conditions(),
        "config_hash": cfg.config_hash(),
    }


@router.get("/local-model/health")
async def local_model_health():
    try:
        return await OllamaProvider().health()
    except Exception:
        configured_model = os.getenv("LOCAL_LLM_MODEL", "qwen3:4b").strip() or "qwen3:4b"
        return {
            "ok": False,
            # Keep the legacy error key for the existing frontend while
            # avoiding raw provider bodies and connection details.
            "error": "Local Ollama health check failed",
            "code": "LOCAL_MODEL_UNAVAILABLE",
            "message": "Local Ollama health check failed",
            "retryable": True,
            "configured_model": configured_model,
        }


@router.get("/sources")
def list_sources(runtime: ApiRuntime = Depends(get_api_runtime)):
    return {
        "snapshot_id": runtime.source_store.snapshot_id(),
        "sources": runtime.source_store.list_sources(),
    }


@router.get("/sources/{source_id}")
def get_source(source_id: str, runtime: ApiRuntime = Depends(get_api_runtime)):
    item = runtime.source_store.source(source_id)
    if not item:
        raise ApiError(404, "NOT_FOUND", "source not found")
    return item


@router.get("/chunks/{chunk_id}")
def get_chunk(chunk_id: str, runtime: ApiRuntime = Depends(get_api_runtime)):
    item = runtime.source_store.chunk(chunk_id)
    if not item:
        raise ApiError(404, "NOT_FOUND", "chunk not found")
    return item


@router.post("/sources/text")
def import_text(
    body: SourceTextRequest,
    runtime: ApiRuntime = Depends(get_api_runtime),
):
    if not body.source_name.strip():
        raise ApiError(400, "SOURCE_NAME_REQUIRED", "source_name is required")
    if not body.text.strip():
        raise ApiError(400, "EMPTY_SOURCE", "text is empty")
    return runtime.source_store.import_text(body.source_name, body.text)


@router.post("/sources/file")
async def import_file(
    file: UploadFile = File(...),
    runtime: ApiRuntime = Depends(get_api_runtime),
):
    data = await file.read(MAX_SOURCE_BYTES + 1)
    if len(data) > MAX_SOURCE_BYTES:
        raise ApiError(413, "PAYLOAD_TOO_LARGE", "M0 only accepts UTF-8 text/code/markdown files up to 2 MB")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise ApiError(415, "UNSUPPORTED_ENCODING", "M0 accepts UTF-8 text/code/markdown files only")
    if not text.strip():
        raise ApiError(400, "EMPTY_SOURCE", "file is empty")
    filename = (file.filename or "").strip() or "upload.txt"
    return runtime.source_store.import_text(filename, text)


@router.post("/chat")
async def chat(
    body: ChatRequest,
    runtime: ApiRuntime = Depends(get_api_runtime),
):
    if not body.message.strip():
        raise ApiError(400, "MESSAGE_REQUIRED", "message is required")
    try:
        run = await runtime.pipeline.run(body.message.strip(), body.condition, body.provider)
        return run
    except ValueError as exc:
        raise _pipeline_value_error(exc) from exc


@router.get("/runs")
def list_runs(runtime: ApiRuntime = Depends(get_api_runtime)):
    return runtime.run_store.list()


@router.get("/runs/{run_id}")
def get_run(run_id: str, runtime: ApiRuntime = Depends(get_api_runtime)):
    run = runtime.run_store.get(run_id)
    if not run:
        raise ApiError(404, "NOT_FOUND", "run not found")
    return run
