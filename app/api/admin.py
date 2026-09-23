from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from app.api.common import runtime_config
from app.api.dependencies import get_admin_user, get_api_runtime, get_auth_store
from app.auth.store import AuthStore
from app.core.api_runtime import ApiRuntime


router = APIRouter()


@router.get("/admin/status")
def admin_status(
    runtime: ApiRuntime = Depends(get_api_runtime),
    _admin: dict[str, Any] = Depends(get_admin_user),
    store: AuthStore = Depends(get_auth_store),
) -> dict[str, Any]:
    cfg = runtime_config()
    return {
        "ok": True,
        "local_only": True,
        "auth": store.status(),
        "runtime": {
            "implementation_profile": cfg.implementation_profile,
            "provider": cfg.provider,
            "local_model": cfg.local_model,
            "allowed_conditions": cfg.allowed_conditions(),
            "config_hash": cfg.config_hash(),
        },
        "source_snapshot_id": runtime.source_store.snapshot_id(),
    }

@router.get("/admin/users")
def admin_users(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _admin: dict[str, Any] = Depends(get_admin_user),
    store: AuthStore = Depends(get_auth_store),
) -> dict[str, Any]:
    return {
        "users": store.list_users(limit=limit, offset=offset),
        "total": store.user_count(),
        "limit": limit,
        "offset": offset,
    }
