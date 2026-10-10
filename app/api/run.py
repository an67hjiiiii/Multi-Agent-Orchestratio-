from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from app.api.common import run_or_404
from app.api.dependencies import get_api_runtime, get_current_user
from app.api.knowledge import source_owner_id
from app.core.api_runtime import ApiRuntime


router = APIRouter()


@router.get("/runs")
def list_runs(
    user: dict[str, Any] = Depends(get_current_user),
    runtime: ApiRuntime = Depends(get_api_runtime),
    limit: int = Query(default=30, ge=1, le=500),
):
    return runtime.run_store.list(limit=limit, owner_id=source_owner_id(user))


@router.get("/runs/{run_id}")
def get_run(
    run_id: str,
    user: dict[str, Any] = Depends(get_current_user),
    runtime: ApiRuntime = Depends(get_api_runtime),
):
    return run_or_404(run_id, runtime, user)


@router.get("/history")
def history(
    user: dict[str, Any] = Depends(get_current_user),
    runtime: ApiRuntime = Depends(get_api_runtime),
    limit: int = Query(default=30, ge=1, le=500),
):
    return runtime.run_store.list(limit=limit, owner_id=source_owner_id(user))
