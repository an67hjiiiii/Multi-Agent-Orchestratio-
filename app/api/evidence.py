from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.common import run_evidence_ids, run_or_404
from app.api.dependencies import get_api_runtime
from app.api.knowledge import call_knowledge_method, chunk_record, knowledge_service
from app.core.api_runtime import ApiRuntime
from app.run.trace import persisted_run_events


router = APIRouter()


@router.get("/runs/{run_id}/evidence")
def get_run_evidence(run_id: str, runtime: ApiRuntime = Depends(get_api_runtime)) -> dict:
    run = run_or_404(run_id, runtime)
    events = persisted_run_events(run)
    evidence_ids = run_evidence_ids(run, events)
    service = knowledge_service(runtime)
    items: list[dict] = []
    missing_ids: list[str] = []
    for evidence_id in evidence_ids:
        chunk = (
            runtime.source_store.chunk(evidence_id)
            if service is None
            else call_knowledge_method(runtime, "chunk", evidence_id)
        )
        if chunk is None:
            missing_ids.append(evidence_id)
            continue
        items.append(chunk_record(chunk))
    return {
        "run_id": run_id,
        "source_snapshot_id": run.get("source_snapshot_id", runtime.source_store.snapshot_id()),
        "evidence_ids": evidence_ids,
        "items": items,
        "evidence": items,
        "missing_ids": missing_ids,
    }
