from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_api_runtime, get_current_user
from app.api.errors import ApiError
from app.api.knowledge import (
    call_knowledge_method,
    chunk_record,
    knowledge_service,
    knowledge_status,
    source_owner_id,
)
from app.core.api_runtime import ApiRuntime
from app.retrieval.query import retrieve_chunks


router = APIRouter()


@router.get("/kb/search")
def search_knowledge_base(
    query: str | None = Query(default=None),
    q: str | None = Query(default=None),
    top_k: int = Query(default=6, ge=1, le=50),
    min_score: float = Query(default=0.0, ge=0.0),
    domain: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
    runtime: ApiRuntime = Depends(get_api_runtime),
):
    request = (query if query is not None else q or "").strip()
    if not request:
        raise ApiError(400, "QUERY_REQUIRED", "query is required")
    try:
        service = knowledge_service(runtime)
        owner_id = source_owner_id(user)
        results = (
            retrieve_chunks(
                request,
                [
                    chunk
                    for chunk in runtime.source_store.chunks()
                    if chunk.provenance.get("owner_user_id") == owner_id
                ],
                retrieval_mode="LEXICAL",
                vector_store=None,
                embedder=None,
                top_k=top_k,
                min_score=min_score,
                domain=domain,
                owner_id=owner_id,
            )
            if service is None
            else call_knowledge_method(
                runtime,
                "search",
                request,
                top_k=top_k,
                min_score=min_score,
                domain=domain,
                owner_id=owner_id,
            )
        )
    except ValueError as exc:
        raise ApiError(400, "INVALID_SEARCH", str(exc)) from exc
    return {
        "query": request,
        "snapshot_id": runtime.source_store.snapshot_id(),
        "retrieval_backend": knowledge_status(runtime)["retrieval_backend"],
        "results": [chunk_record(chunk) for chunk in results],
    }
