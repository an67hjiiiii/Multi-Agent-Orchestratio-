from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.api.dependencies import get_api_runtime, get_auth_store, get_session_token
from app.auth.store import AuthStore, InvalidSessionError
from app.core.api_runtime import ApiRuntime
from app.api.common import runtime_config
from app.api.knowledge import knowledge_status


router = APIRouter()


@router.get("/health")
def health(runtime: ApiRuntime = Depends(get_api_runtime)):
    cfg = runtime_config()
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
    cfg = runtime_config()
    return {
        **cfg.public_dict(),
        "allowed_conditions": cfg.allowed_conditions(),
        "config_hash": cfg.config_hash(),
    }


@router.get("/settings")
def settings(
    runtime: ApiRuntime = Depends(get_api_runtime),
    token: str | None = Depends(get_session_token),
    store: AuthStore = Depends(get_auth_store),
) -> dict[str, Any]:
    cfg = runtime_config()
    current_user: dict[str, Any] | None = None
    if token:
        try:
            current_user = store.resolve(token)
        except InvalidSessionError:
            current_user = None
    return {
        "local_only": True,
        "auth_enabled": True,
        "user": current_user,
        "runtime": {
            **cfg.public_dict(),
            "allowed_conditions": cfg.allowed_conditions(),
            "config_hash": cfg.config_hash(),
        },
        "source_snapshot_id": runtime.source_store.snapshot_id(),
        "knowledge_base": knowledge_status(runtime),
    }
