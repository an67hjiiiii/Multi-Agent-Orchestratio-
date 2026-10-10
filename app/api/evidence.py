from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.api.common import run_evidence_ids, run_or_404
from app.api.dependencies import get_api_runtime, get_current_user
from app.api.knowledge import (
    call_knowledge_method,
    chunk_record,
    knowledge_service,
    source_is_owned_by,
    source_owner_id,
)
from app.core.api_runtime import ApiRuntime
from app.run.trace import persisted_run_events


router = APIRouter()


@router.get("/runs/{run_id}/evidence")
def get_run_evidence(
    run_id: str,
    user: dict[str, Any] = Depends(get_current_user),
    runtime: ApiRuntime = Depends(get_api_runtime),
) -> dict:
    run = run_or_404(run_id, runtime, user)
    events = persisted_run_events(run)
    evidence_ids = run_evidence_ids(run, events)
    service = knowledge_service(runtime)
    items: list[dict] = []
    owned_ids: list[str] = []
    for evidence_id in evidence_ids:
        chunk = (
            runtime.source_store.chunk(evidence_id)
            if service is None
            else call_knowledge_method(runtime, "chunk", evidence_id)
        )
        if chunk is None:
            # Ownership cannot be established for a missing chunk ID.
            continue
        item = chunk_record(chunk)
        if not source_is_owned_by(item, source_owner_id(user)):
            continue
        owned_ids.append(evidence_id)
        items.append(item)
    return {
        "run_id": run_id,
        "source_snapshot_id": run.get("source_snapshot_id", runtime.source_store.snapshot_id()),
        "evidence_ids": owned_ids,
        "items": items,
        "evidence": items,
        "missing_ids": [],
    }
