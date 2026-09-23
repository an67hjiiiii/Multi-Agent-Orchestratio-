from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.common import run_or_404
from app.api.dependencies import get_api_runtime
from app.core.api_runtime import ApiRuntime


router = APIRouter()


@router.get("/runs")
def list_runs(
    runtime: ApiRuntime = Depends(get_api_runtime),
    limit: int = Query(default=30, ge=1, le=500),
):
    return runtime.run_store.list(limit=limit)
@router.get("/runs/{run_id}")
def get_run(run_id: str, runtime: ApiRuntime = Depends(get_api_runtime)):
    return run_or_404(run_id, runtime)


@router.get("/history")
def history(
    runtime: ApiRuntime = Depends(get_api_runtime),
    limit: int = Query(default=30, ge=1, le=500),
):
    return runtime.run_store.list(limit=limit)
