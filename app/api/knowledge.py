from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from typing import Any

from fastapi import APIRouter, Depends, File, Query, UploadFile

from app.api.dependencies import get_api_runtime
from app.api.errors import ApiError
from app.api.schemas import SourceTextRequest
from app.core.api_runtime import ApiRuntime
from app.ingestion.documents import DocumentTypeError


router = APIRouter()
MAX_SOURCE_BYTES = 2_000_000


def vector_backend_requested() -> bool:
    """Return whether vector or hybrid retrieval was explicitly requested."""

    mode = os.getenv("RETRIEVAL_MODE", "").strip().upper()
    if mode:
        return mode in {"VECTOR", "HYBRID"}
    return bool(os.getenv("VECTOR_BACKEND", "").strip())


def knowledge_service(runtime: ApiRuntime) -> Any | None:
    """Resolve the optional KnowledgeBase without changing the lexical LKG."""

    service = getattr(runtime, "knowledge_base", None)
    if vector_backend_requested():
        backend_name = str(getattr(service, "backend_name", "")).strip().lower()
        vector_store = getattr(service, "vector_store", None)
        if service is None or vector_store is None or backend_name in {"", "lexical", "unavailable"}:
            raise ApiError(
                503,
                "KNOWLEDGE_BASE_UNAVAILABLE",
                "Configured vector knowledge base is unavailable",
                retryable=True,
            )
    return service


def knowledge_method(runtime: ApiRuntime, name: str) -> Callable[..., Any]:
    service = knowledge_service(runtime)
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


def lexical_status(runtime: ApiRuntime) -> dict[str, Any]:
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


def call_knowledge_method(
    runtime: ApiRuntime,
    name: str,
    *args: Any,
    **kwargs: Any,
) -> Any:
    method = knowledge_method(runtime, name)
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


def as_record(value: Any, *, error_code: str) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    attributes = getattr(value, "__dict__", None)
    if isinstance(attributes, dict):
        return dict(attributes)
    raise ApiError(500, error_code, "Knowledge-base service returned an invalid record")


def chunk_record(value: Any) -> dict[str, Any]:
    record = as_record(value, error_code="INVALID_KNOWLEDGE_CHUNK")
    provenance = record.get("provenance")
    if isinstance(provenance, dict):
        record["provenance"] = dict(provenance)
    return record


def call_knowledge_import(
    runtime: ApiRuntime,
    name: str,
    *args: Any,
    **kwargs: Any,
) -> dict[str, Any]:
    method = knowledge_method(runtime, name)
    try:
        value = method(*args, **kwargs)
    except DocumentTypeError as exc:
        detail = str(exc)
        if "requires the optional pypdf dependency" in detail:
            raise ApiError(503, "PDF_EXTRACTION_UNAVAILABLE", detail, retryable=True) from exc
        if "no extractable text" in detail:
            raise ApiError(422, "PDF_NO_TEXT", detail) from exc
        raise ApiError(415, "UNSUPPORTED_DOCUMENT_TYPE", detail) from exc
    except UnicodeDecodeError as exc:
        raise ApiError(415, "UNSUPPORTED_ENCODING", "document must be valid UTF-8") from exc
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
    return as_record(value, error_code="INVALID_KNOWLEDGE_IMPORT")


def knowledge_status(runtime: ApiRuntime) -> dict[str, Any]:
    service = knowledge_service(runtime)
    if service is None:
        return lexical_status(runtime)
    status = as_record(
        call_knowledge_method(runtime, "status"),
        error_code="INVALID_KNOWLEDGE_STATUS",
    )
    retrieval_backend = str(status.get("retrieval_backend") or "").strip()
    try:
        vector_indexed_chunks = max(0, int(status.get("vector_indexed_chunks", 0)))
    except (TypeError, ValueError):
        vector_indexed_chunks = 0
    try:
        chunk_count = max(0, int(status.get("chunk_count", len(runtime.source_store.chunks()))))
    except (TypeError, ValueError):
        chunk_count = len(runtime.source_store.chunks())
    try:
        source_count = max(0, int(status.get("source_count", len(runtime.source_store.list_sources()))))
    except (TypeError, ValueError):
        source_count = len(runtime.source_store.list_sources())

    if not retrieval_backend:
        retrieval_backend = "lexical" if vector_indexed_chunks == 0 else "vector"
    normalized = {
        "status": status.get(
            "status",
            "READY"
            if (retrieval_backend == "lexical" and chunk_count > 0) or vector_indexed_chunks > 0
            else "EMPTY"
            if retrieval_backend == "lexical"
            else "UNAVAILABLE",
        ),
        "backend": status.get(
            "backend",
            "local_json" if retrieval_backend == "lexical" else retrieval_backend,
        ),
        "retrieval_backend": retrieval_backend,
        "embedding_version": status.get("embedding_version"),
        "vector_indexed_chunks": vector_indexed_chunks,
        "index_identity": status.get("index_identity"),
        "index_status": status.get(
            "index_status",
            "NOT_CONFIGURED"
            if retrieval_backend == "lexical"
            else "READY"
            if vector_indexed_chunks > 0
            else "EMPTY"
            if chunk_count == 0
            else "UNAVAILABLE",
        ),
        "source_count": source_count,
        "chunk_count": chunk_count,
        "snapshot_id": status.get("snapshot_id", runtime.source_store.snapshot_id()),
    }
    if retrieval_backend != "lexical":
        normalized["retrieval_mode"] = str(status.get("retrieval_mode") or retrieval_backend).upper()
    return normalized


@router.get("/sources")
def list_sources(runtime: ApiRuntime = Depends(get_api_runtime)):
    service = knowledge_service(runtime)
    sources = (
        runtime.source_store.list_sources()
        if service is None
        else call_knowledge_method(runtime, "list_sources")
    )
    return {"snapshot_id": runtime.source_store.snapshot_id(), "sources": sources}


@router.get("/sources/{source_id}")
def get_source(source_id: str, runtime: ApiRuntime = Depends(get_api_runtime)):
    service = knowledge_service(runtime)
    item = (
        runtime.source_store.source(source_id)
        if service is None
        else call_knowledge_method(runtime, "source", source_id)
    )
    if not item:
        raise ApiError(404, "NOT_FOUND", "source not found")
    return as_record(item, error_code="INVALID_KNOWLEDGE_SOURCE")


@router.get("/chunks/{chunk_id}")
def get_chunk(chunk_id: str, runtime: ApiRuntime = Depends(get_api_runtime)):
    service = knowledge_service(runtime)
    item = (
        runtime.source_store.chunk(chunk_id)
        if service is None
        else call_knowledge_method(runtime, "chunk", chunk_id)
    )
    if not item:
        raise ApiError(404, "NOT_FOUND", "chunk not found")
    return chunk_record(item)


@router.post("/sources/text")
def import_text(body: SourceTextRequest, runtime: ApiRuntime = Depends(get_api_runtime)):
    if not body.source_name.strip():
        raise ApiError(400, "SOURCE_NAME_REQUIRED", "source_name is required")
    if not body.text.strip():
        raise ApiError(400, "EMPTY_SOURCE", "text is empty")
    service = knowledge_service(runtime)
    if service is None:
        return runtime.source_store.import_text(body.source_name, body.text)
    return call_knowledge_import(
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
    service = knowledge_service(runtime)
    filename = (file.filename or "").strip() or "upload.txt"
    if service is not None:
        return call_knowledge_import(
            runtime,
            "import_document",
            filename,
            data,
            origin="upload",
            content_type=file.content_type,
        )
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ApiError(415, "UNSUPPORTED_ENCODING", "M0 accepts UTF-8 text/code/markdown files only") from exc
    if not text.strip():
        raise ApiError(400, "EMPTY_SOURCE", "file is empty")
    return runtime.source_store.import_text(filename, text)


@router.get("/kb/status")
def kb_status(runtime: ApiRuntime = Depends(get_api_runtime)):
    return knowledge_status(runtime)


@router.get("/kb/sources")
def list_knowledge_base_sources(runtime: ApiRuntime = Depends(get_api_runtime)):
    return list_sources(runtime)


@router.get("/kb/sources/{source_id}")
def inspect_knowledge_base_source(source_id: str, runtime: ApiRuntime = Depends(get_api_runtime)):
    return get_source(source_id, runtime)


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
