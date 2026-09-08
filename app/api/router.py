from __future__ import annotations

import inspect
import os
from collections.abc import Awaitable, Callable, Mapping
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
from app.retrieval.text import retrieve


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


def _vector_backend_requested() -> bool:
    """Return whether the caller explicitly requested a vector backend."""

    return bool(os.getenv("VECTOR_BACKEND", "").strip())


def _knowledge_service(runtime: ApiRuntime) -> Any | None:
    """Resolve the optional KnowledgeBase without changing the lexical LKG.

    The Knowledge Engine owns the concrete service and its storage/provider
    configuration.  Until that service is present, the existing SourceStore
    remains the explicit lexical path.  An explicit vector configuration must
    never silently fall back to that path.
    """

    service = getattr(runtime, "knowledge_base", None)
    if service is None and _vector_backend_requested():
        raise ApiError(
            503,
            "KNOWLEDGE_BASE_UNAVAILABLE",
            "Configured vector knowledge base is unavailable",
            retryable=True,
        )
    return service


def _knowledge_method(runtime: ApiRuntime, name: str) -> Callable[..., Any]:
    service = _knowledge_service(runtime)
    if service is None:
        raise ApiError(
            503,
            "KNOWLEDGE_BASE_UNAVAILABLE",
            "Knowledge-base service is unavailable",
            retryable=True,
        )
    method = getattr(service, name, None)
    if not callable(method):
        raise ApiError(
            503,
            "KNOWLEDGE_BASE_UNAVAILABLE",
            "Knowledge-base service is unavailable",
            retryable=True,
        )
    return method


def _lexical_status(runtime: ApiRuntime) -> dict[str, Any]:
    """Describe the current SourceStore path without implying vector search."""

    chunks = runtime.source_store.chunks()
    return {
        "status": "READY" if chunks else "EMPTY",
        "backend": "local_json",
        "retrieval_backend": "lexical",
        "embedding_version": None,
        "vector_indexed_chunks": 0,
        "index_identity": None,
        "index_status": "NOT_CONFIGURED",
        "source_count": len(runtime.source_store.list_sources()),
        "chunk_count": len(chunks),
        "snapshot_id": runtime.source_store.snapshot_id(),
    }


def _call_knowledge_method(
    runtime: ApiRuntime,
    name: str,
    *args: Any,
    **kwargs: Any,
) -> Any:
    method = _knowledge_method(runtime, name)
    try:
        return method(*args, **kwargs)
    except ApiError:
        raise
    except Exception as exc:
        raise ApiError(
            503,
            "KNOWLEDGE_BASE_UNAVAILABLE",
            "Knowledge-base operation is unavailable",
            retryable=True,
        ) from exc


def _as_record(value: Any, *, error_code: str) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    attributes = getattr(value, "__dict__", None)
    if isinstance(attributes, dict):
        return dict(attributes)
    raise ApiError(500, error_code, "Knowledge-base service returned an invalid record")


def _chunk_record(value: Any) -> dict[str, Any]:
    record = _as_record(value, error_code="INVALID_KNOWLEDGE_CHUNK")
    provenance = record.get("provenance")
    if isinstance(provenance, Mapping):
        record["provenance"] = dict(provenance)
    return record


def _call_knowledge_import(
    runtime: ApiRuntime,
    name: str,
    *args: Any,
    **kwargs: Any,
) -> dict[str, Any]:
    method = _knowledge_method(runtime, name)
    try:
        value = method(*args, **kwargs)
    except DocumentTypeError as exc:
        raise ApiError(415, "UNSUPPORTED_DOCUMENT_TYPE", str(exc)) from exc
    except UnicodeDecodeError as exc:
        raise ApiError(
            415,
            "UNSUPPORTED_ENCODING",
            "document must be valid UTF-8",
        ) from exc
    except ValueError as exc:
        detail = str(exc).strip()
        if "size limit" in detail:
            raise ApiError(413, "PAYLOAD_TOO_LARGE", detail) from exc
        if "must not be empty" in detail or "text is empty" in detail:
            raise ApiError(400, "EMPTY_SOURCE", "file is empty") from exc
        raise ApiError(400, "INVALID_DOCUMENT", detail or "document is invalid") from exc
    except Exception as exc:
        raise ApiError(
            503,
            "KNOWLEDGE_BASE_UNAVAILABLE",
            "Knowledge-base import is unavailable",
            retryable=True,
        ) from exc
    return _as_record(value, error_code="INVALID_KNOWLEDGE_IMPORT")


def _knowledge_status(runtime: ApiRuntime) -> dict[str, Any]:
    service = _knowledge_service(runtime)
    if service is None:
        return _lexical_status(runtime)
    status = _as_record(
        _call_knowledge_method(runtime, "status"),
        error_code="INVALID_KNOWLEDGE_STATUS",
    )
    retrieval_backend = str(status.get("retrieval_backend") or "").strip()
    vector_indexed_chunks = status.get("vector_indexed_chunks", 0)
    try:
        vector_indexed_chunks = max(0, int(vector_indexed_chunks))
    except (TypeError, ValueError):
        vector_indexed_chunks = 0
    chunk_count = status.get("chunk_count", len(runtime.source_store.chunks()))
    source_count = status.get("source_count", len(runtime.source_store.list_sources()))
    try:
        chunk_count = max(0, int(chunk_count))
    except (TypeError, ValueError):
        chunk_count = len(runtime.source_store.chunks())
    try:
        source_count = max(0, int(source_count))
    except (TypeError, ValueError):
        source_count = len(runtime.source_store.list_sources())

    if not retrieval_backend:
        retrieval_backend = "lexical" if vector_indexed_chunks == 0 else "vector"
    status.setdefault(
        "status",
        "READY"
        if (retrieval_backend == "lexical" and chunk_count > 0)
        or vector_indexed_chunks > 0
        else "EMPTY"
        if retrieval_backend == "lexical"
        else "UNAVAILABLE",
    )
    status.setdefault(
        "backend",
        "local_json" if retrieval_backend == "lexical" else retrieval_backend,
    )
    status.setdefault("retrieval_backend", retrieval_backend)
    status.setdefault("embedding_version", None)
    status["vector_indexed_chunks"] = vector_indexed_chunks
    status.setdefault("index_identity", None)
    status.setdefault(
        "index_status",
        "NOT_CONFIGURED"
        if retrieval_backend == "lexical"
        else "READY"
        if vector_indexed_chunks > 0
        else "EMPTY"
        if chunk_count == 0
        else "UNAVAILABLE",
    )
    status["source_count"] = source_count
    status["chunk_count"] = chunk_count
    status.setdefault("snapshot_id", runtime.source_store.snapshot_id())
    return status


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
    service = _knowledge_service(runtime)
    sources = (
        runtime.source_store.list_sources()
        if service is None
        else _call_knowledge_method(runtime, "list_sources")
    )
    return {
        "snapshot_id": runtime.source_store.snapshot_id(),
        "sources": sources,
    }


@router.get("/sources/{source_id}")
def get_source(source_id: str, runtime: ApiRuntime = Depends(get_api_runtime)):
    service = _knowledge_service(runtime)
    item = (
        runtime.source_store.source(source_id)
        if service is None
        else _call_knowledge_method(runtime, "source", source_id)
    )
    if not item:
        raise ApiError(404, "NOT_FOUND", "source not found")
    return _as_record(item, error_code="INVALID_KNOWLEDGE_SOURCE")


@router.get("/chunks/{chunk_id}")
def get_chunk(chunk_id: str, runtime: ApiRuntime = Depends(get_api_runtime)):
    service = _knowledge_service(runtime)
    item = (
        runtime.source_store.chunk(chunk_id)
        if service is None
        else _call_knowledge_method(runtime, "chunk", chunk_id)
    )
    if not item:
        raise ApiError(404, "NOT_FOUND", "chunk not found")
    return _chunk_record(item)


@router.post("/sources/text")
def import_text(
    body: SourceTextRequest,
    runtime: ApiRuntime = Depends(get_api_runtime),
):
    if not body.source_name.strip():
        raise ApiError(400, "SOURCE_NAME_REQUIRED", "source_name is required")
    if not body.text.strip():
        raise ApiError(400, "EMPTY_SOURCE", "text is empty")
    service = _knowledge_service(runtime)
    if service is None:
        return runtime.source_store.import_text(body.source_name, body.text)
    return _call_knowledge_import(
        runtime,
        "import_text",
        body.source_name,
        body.text,
        provenance={
            "ingestion_version": "api-text-v1",
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
    if len(data) > MAX_SOURCE_BYTES:
        raise ApiError(413, "PAYLOAD_TOO_LARGE", "M0 only accepts UTF-8 text/code/markdown files up to 2 MB")
    service = _knowledge_service(runtime)
    filename = (file.filename or "").strip() or "upload.txt"
    if service is not None:
        return _call_knowledge_import(
            runtime,
            "import_document",
            filename,
            data,
            origin="upload",
            content_type=file.content_type,
        )
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise ApiError(415, "UNSUPPORTED_ENCODING", "M0 accepts UTF-8 text/code/markdown files only")
    if not text.strip():
        raise ApiError(400, "EMPTY_SOURCE", "file is empty")
    return runtime.source_store.import_text(filename, text)


@router.get("/kb/status")
def kb_status(runtime: ApiRuntime = Depends(get_api_runtime)):
    return _knowledge_status(runtime)


@router.get("/kb/sources")
def list_knowledge_base_sources(runtime: ApiRuntime = Depends(get_api_runtime)):
    return list_sources(runtime)


@router.get("/kb/sources/{source_id}")
def inspect_knowledge_base_source(
    source_id: str,
    runtime: ApiRuntime = Depends(get_api_runtime),
):
    return get_source(source_id, runtime)


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
        service = _knowledge_service(runtime)
        results = (
            retrieve(
                request,
                runtime.source_store.chunks(),
                top_k=top_k,
                min_score=min_score,
                domain=domain,
            )
            if service is None
            else _call_knowledge_method(
                runtime,
                "search",
                request,
                top_k=top_k,
                min_score=min_score,
                domain=domain,
            )
        )
    except ValueError as exc:
        raise ApiError(400, "INVALID_SEARCH", str(exc)) from exc
    return {
        "query": request,
        "snapshot_id": runtime.source_store.snapshot_id(),
        "retrieval_backend": _knowledge_status(runtime)["retrieval_backend"],
        "results": [_chunk_record(chunk) for chunk in results],
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
    # An explicitly configured vector path must be wired before chat can use
    # the corpus; otherwise the legacy lexical store would be a silent
    # fallback for a request that selected a different retrieval backend.
    _knowledge_service(runtime)
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
