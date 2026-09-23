from __future__ import annotations

import inspect
import os
from typing import Any

from fastapi import APIRouter, Depends

from app.api.common import (
    PLiteCallable,
    assert_plite_profile,
    get_p_lite_pipeline,
    planning_value_error,
    validate_decomposition_result,
)
from app.api.errors import ApiError
from app.api.schemas import DECOMPOSITION_RESPONSE_MODEL, DecompositionRequest
from app.providers.ollama import OllamaProvider


router = APIRouter()


@router.post("/tasks/decompose", response_model=DECOMPOSITION_RESPONSE_MODEL)
async def decompose_tasks(
    body: DecompositionRequest,
    pipeline: PLiteCallable = Depends(get_p_lite_pipeline),
) -> Any:
    assert_plite_profile()
    request = body.request.strip()
    if not request:
        raise ApiError(400, "REQUEST_REQUIRED", "request is required")

    try:
        value = pipeline(request) if body.provider is None else pipeline(request, body.provider)
        if inspect.isawaitable(value):
            value = await value
        return validate_decomposition_result(value)
    except ApiError:
        raise
    except ValueError as exc:
        raise planning_value_error(exc) from exc
    except Exception as exc:
        raise ApiError(500, "PLITE_FAILED", "P-lite pipeline failed") from exc


@router.get("/local-model/health")
async def local_model_health():
    try:
        return await OllamaProvider().health()
    except Exception:
        configured_model = os.getenv("LOCAL_LLM_MODEL", "qwen3:4b").strip() or "qwen3:4b"
        return {
            "ok": False,
            "error": "Local Ollama health check failed",
            "code": "LOCAL_MODEL_UNAVAILABLE",
            "message": "Local Ollama health check failed",
            "retryable": True,
            "configured_model": configured_model,
        }
