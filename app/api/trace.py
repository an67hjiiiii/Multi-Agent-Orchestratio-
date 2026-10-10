from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from fastapi import APIRouter, Depends

from app.api.common import run_or_404
from app.api.dependencies import get_api_runtime, get_current_user
from app.core.api_runtime import ApiRuntime
from app.run.trace import persisted_run_events


router = APIRouter()


@router.get("/runs/{run_id}/trace")
def get_run_trace(
    run_id: str,
    user: dict[str, Any] = Depends(get_current_user),
    runtime: ApiRuntime = Depends(get_api_runtime),
) -> dict[str, Any]:
    run = run_or_404(run_id, runtime, user)
    events = persisted_run_events(run)
    return {
        "run_id": run_id,
        "status": run.get("status"),
        "events": events,
        "trace": events,
        "effective_config": run.get("effective_config"),
        "metrics": run.get("metrics") if isinstance(run.get("metrics"), Mapping) else {},
    }
