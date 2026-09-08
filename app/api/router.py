from __future__ import annotations

import inspect
import os
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import APIRouter, Depends, File, Query, UploadFile
from pydantic import ValidationError

from app.api.dependencies import get_api_runtime
from app.api.errors import ApiError
from app.api.schemas import (
    DECOMPOSITION_RESPONSE_MODEL,
    ChatRequest,
    DecompositionRequest,
    SourceTextRequest,
)
from app.core.api_runtime import ApiRuntime
from app.core.config import RuntimeConfig
from app.ingestion.documents import DocumentTypeError
from app.providers.ollama import OllamaProvider


router = APIRouter(prefix="/api")
MAX_SOURCE_BYTES = 2_000_000
PLITE_PROFILES = frozenset({"dev", "m1", "m2"})
PLiteCallable = Callable[[str, str | None], Awaitable[Any] | Any]


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


def _assert_plite_profile() -> None:
    cfg = _runtime_config()
    if cfg.implementation_profile not in PLITE_PROFILES:
        raise ApiError(
            400,
            "UNSUPPORTED_IMPLEMENTATION",
            f"P-lite is not available in profile {cfg.implementation_profile}",
        )


def get_p_lite_pipeline(
    runtime: ApiRuntime = Depends(get_api_runtime),
) -> PLiteCallable:
    """Resolve the separately wired P-lite callable without touching M0.

    The integration boundary installs ``p_lite_pipeline`` on ``ApiRuntime``.
    Keeping resolution here lets the API be tested with a dependency override
    and prevents a missing future implementation from falling back to M0 chat.
    """

    _assert_plite_profile()
    pipeline = getattr(runtime, "p_lite_pipeline", None)
    if pipeline is None:
        raise ApiError(
            503,
            "PLITE_UNAVAILABLE",
            "P-lite pipeline is unavailable",
            retryable=True,
        )

    if callable(pipeline):
        return pipeline

    run = getattr(pipeline, "run", None)
    if callable(run):
        return run

    raise ApiError(
        503,
        "PLITE_UNAVAILABLE",
        "P-lite pipeline is unavailable",
        retryable=True,
    )


def _validate_decomposition_result(value: Any) -> Any:
    """Validate the pipeline output with the locked research contract.

    The schema worker is integrated in a later commit than this API worker, so
    the import is intentionally deferred. Once present, no API-local task
    shape is accepted in place of ``DecompositionResult``.
    """

    if DECOMPOSITION_RESPONSE_MODEL is None:
        return value

    if isinstance(value, DECOMPOSITION_RESPONSE_MODEL):
        return value

    try:
        return DECOMPOSITION_RESPONSE_MODEL.model_validate(value)
    except (TypeError, ValueError, ValidationError) as exc:
        raise ApiError(
            500,
            "INVALID_DECOMPOSITION",
            "P-lite pipeline returned an invalid decomposition",
        ) from exc


def _planning_value_error(exc: ValueError) -> ApiError:
    detail = str(exc).strip()
    if detail.startswith("Only fake and local Ollama providers"):
        return _pipeline_value_error(exc)
    if detail.startswith("Condition ") or detail.startswith("Unknown condition"):
        return _pipeline_value_error(exc)
    return ApiError(
        400,
        "INVALID_DECOMPOSITION",
        detail or "P-lite request could not be processed",
    )


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
        "knowledge_base": runtime.knowledge_base.status(),
    }


@router.get("/config")
def config():
    cfg = _runtime_config()
    return {
        **cfg.public_dict(),
        "allowed_conditions": cfg.allowed_conditions(),
        "config_hash": cfg.config_hash(),
    }


@router.post("/tasks/decompose", response_model=DECOMPOSITION_RESPONSE_MODEL)
async def decompose_tasks(
    body: DecompositionRequest,
    pipeline: PLiteCallable = Depends(get_p_lite_pipeline),
) -> Any:
    """Return the bounded P-lite task plan for inspection."""

    _assert_plite_profile()
    request = body.request.strip()
    if not request:
        raise ApiError(400, "REQUEST_REQUIRED", "request is required")

    try:
        value = pipeline(request) if body.provider is None else pipeline(request, body.provider)
        if inspect.isawaitable(value):
            value = await value
        return _validate_decomposition_result(value)
    except ApiError:
        raise
    except ValueError as exc:
        raise _planning_value_error(exc) from exc
    except Exception as exc:
        raise ApiError(
            500,
            "PLITE_FAILED",
            "P-lite pipeline failed",
        ) from exc


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
        "sources": runtime.knowledge_base.list_sources(),
    }


@router.get("/sources/{source_id}")
def get_source(source_id: str, runtime: ApiRuntime = Depends(get_api_runtime)):
    item = runtime.knowledge_base.source(source_id)
    if not item:
        raise ApiError(404, "NOT_FOUND", "source not found")
    return item


@router.get("/chunks/{chunk_id}")
def get_chunk(chunk_id: str, runtime: ApiRuntime = Depends(get_api_runtime)):
    item = runtime.knowledge_base.chunk(chunk_id)
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
    return runtime.knowledge_base.import_text(
        body.source_name,
        body.text,
        provenance={
            "ingestion_version": "kb-v2-text-ingestion-v1",
            "source_type": "text/plain",
            "source_format": "text",
            "origin": "api_text",
        },
    )


@router.post("/sources/file")
async def import_file(
    file: UploadFile = File(...),
    runtime: ApiRuntime = Depends(get_api_runtime),
):
    data = await file.read(MAX_SOURCE_BYTES + 1)
    try:
        return runtime.knowledge_base.import_document(
            (file.filename or "").strip() or "upload.txt",
            data,
            origin="upload",
            content_type=file.content_type,
        )
    except DocumentTypeError as exc:
        raise ApiError(415, "UNSUPPORTED_DOCUMENT_TYPE", str(exc)) from exc
    except UnicodeDecodeError as exc:
        raise ApiError(415, "UNSUPPORTED_ENCODING", "document must be valid UTF-8") from exc
    except ValueError as exc:
        detail = str(exc)
        if "size limit" in detail:
            raise ApiError(413, "PAYLOAD_TOO_LARGE", detail) from exc
        if "must not be empty" in detail:
            raise ApiError(400, "EMPTY_SOURCE", "file is empty") from exc
        raise ApiError(400, "INVALID_DOCUMENT", detail) from exc


@router.get("/kb/status")
def knowledge_base_status(runtime: ApiRuntime = Depends(get_api_runtime)):
    return runtime.knowledge_base.status()


@router.get("/kb/sources")
def list_knowledge_base_sources(runtime: ApiRuntime = Depends(get_api_runtime)):
    return {
        "snapshot_id": runtime.source_store.snapshot_id(),
        "sources": runtime.knowledge_base.list_sources(),
    }


@router.get("/kb/sources/{source_id}")
def inspect_knowledge_base_source(
    source_id: str,
    runtime: ApiRuntime = Depends(get_api_runtime),
):
    item = runtime.knowledge_base.source(source_id)
    if not item:
        raise ApiError(404, "NOT_FOUND", "source not found")
    return item


@router.get("/kb/search")
def search_knowledge_base(
    query: str | None = Query(default=None),
    q: str | None = Query(default=None),
    top_k: int = Query(default=6, ge=1, le=50),
    min_score: float = Query(default=0.0, ge=0.0),
    domain: str | None = Query(default=None),
    runtime: ApiRuntime = Depends(get_api_runtime),
):
    request = (query if query is not None else q or "").strip()
    if not request:
        raise ApiError(400, "QUERY_REQUIRED", "query is required")
    try:
        results = runtime.knowledge_base.search(
            request,
            top_k=top_k,
            min_score=min_score,
            domain=domain,
        )
    except ValueError as exc:
        raise ApiError(400, "INVALID_SEARCH", str(exc)) from exc
    return {
        "query": request,
        "snapshot_id": runtime.source_store.snapshot_id(),
        "retrieval_backend": runtime.knowledge_base.status()["retrieval_backend"],
        "results": [
            {
                **chunk.__dict__,
                "provenance": dict(chunk.provenance),
            }
            for chunk in results
        ],
    }


@router.post("/kb/import/text")
def import_knowledge_base_text(
    body: SourceTextRequest,
    runtime: ApiRuntime = Depends(get_api_runtime),
):
    return import_text(body, runtime)


@router.post("/kb/import/file")
async def import_knowledge_base_file(
    file: UploadFile = File(...),
    runtime: ApiRuntime = Depends(get_api_runtime),
):
    return await import_file(file, runtime)


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
