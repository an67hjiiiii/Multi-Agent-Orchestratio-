from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from fastapi import Depends
from pydantic import ValidationError

from app.api.dependencies import get_api_runtime
from app.api.errors import ApiError
from app.api.schemas import DECOMPOSITION_RESPONSE_MODEL
from app.core.api_runtime import ApiRuntime
from app.core.config import RuntimeConfig


PLITE_PROFILES = frozenset({"dev", "m1", "m2"})
PLiteCallable = Callable[[str, str | None], Awaitable[Any] | Any]


def runtime_config() -> RuntimeConfig:
    try:
        return RuntimeConfig.from_env()
    except (TypeError, ValueError, OverflowError) as exc:
        raise ApiError(
            500,
            "INVALID_CONFIGURATION",
            "Runtime configuration is invalid",
        ) from exc


def pipeline_value_error(exc: ValueError) -> ApiError:
    detail = str(exc)
    if detail.startswith("Condition "):
        code = "UNSUPPORTED_CONDITION"
    elif detail.startswith("Unknown condition"):
        code = "INVALID_CONDITION"
    elif detail.startswith("Only fake and local Ollama providers"):
        code = "UNSUPPORTED_PROVIDER"
    else:
        code = "INVALID_REQUEST"
    return ApiError(400, code, detail or "Request could not be processed")


def assert_plite_profile() -> None:
    cfg = runtime_config()
    if cfg.implementation_profile not in PLITE_PROFILES:
        raise ApiError(
            400,
            "UNSUPPORTED_IMPLEMENTATION",
            f"P-lite is not available in profile {cfg.implementation_profile}",
        )


def get_p_lite_pipeline(
    runtime: ApiRuntime = Depends(get_api_runtime),
) -> PLiteCallable:
    """Resolve the separately wired P-lite callable without touching M0."""

    assert_plite_profile()
    pipeline = getattr(runtime, "p_lite_pipeline", None)
    if pipeline is None:
        raise ApiError(
            503,
            "PLITE_UNAVAILABLE",
            "P-lite pipeline is unavailable",
            retryable=True,
        )

    if callable(pipeline):
        return pipeline

    run = getattr(pipeline, "run", None)
    if callable(run):
        return run

    raise ApiError(
        503,
        "PLITE_UNAVAILABLE",
        "P-lite pipeline is unavailable",
        retryable=True,
    )


def validate_decomposition_result(value: Any) -> Any:
    """Validate pipeline output with the locked research contract."""

    if DECOMPOSITION_RESPONSE_MODEL is None:
        return value

    if isinstance(value, DECOMPOSITION_RESPONSE_MODEL):
        return value

    try:
        return DECOMPOSITION_RESPONSE_MODEL.model_validate(value)
    except (TypeError, ValueError, ValidationError) as exc:
        raise ApiError(
            500,
            "INVALID_DECOMPOSITION",
            "P-lite pipeline returned an invalid decomposition",
        ) from exc


def planning_value_error(exc: ValueError) -> ApiError:
    detail = str(exc).strip()
    if detail.startswith("Only fake and local Ollama providers"):
        return pipeline_value_error(exc)
    if detail.startswith("Condition ") or detail.startswith("Unknown condition"):
        return pipeline_value_error(exc)
    return ApiError(
        400,
        "INVALID_DECOMPOSITION",
        detail or "P-lite request could not be processed",
    )


def run_or_404(
    run_id: str, runtime: ApiRuntime, user: Mapping[str, Any]
) -> dict[str, Any]:
    # RunStore resolves and validates the identifier before ownership is checked.
    run = runtime.run_store.get(run_id)
    owner_id = str(user.get("user_id") or user.get("id") or "").strip()
    if not isinstance(run, Mapping) or not owner_id or run.get("owner_id") != owner_id:
        raise ApiError(404, "NOT_FOUND", "run not found")
    return dict(run)


def conversation_or_404(
    conversation_id: str,
    runtime: ApiRuntime,
    user: Mapping[str, Any],
) -> dict[str, Any]:
    conversation = runtime.conversation_store.get(
        conversation_id,
        str(user.get("user_id") or user.get("id") or ""),
    )
    if conversation is None:
        raise ApiError(404, "NOT_FOUND", "conversation not found")
    return conversation


def run_evidence_ids(run: Mapping[str, Any], events: list[dict[str, Any]]) -> list[str]:
    ids: list[str] = []

    def add(value: Any) -> None:
        if isinstance(value, str) and value.strip() and value not in ids:
            ids.append(value)
        elif isinstance(value, list):
            for item in value:
                add(item)

    add(run.get("citations"))
    add(run.get("evidence_ids"))
    for result in run.get("task_results") or []:
        if isinstance(result, Mapping):
            add(result.get("evidence_ids"))
            add(result.get("citations"))
    for event in events:
        add(event.get("selected"))
        result = event.get("result")
        if isinstance(result, Mapping):
            add(result.get("evidence_ids"))
            add(result.get("citations"))
    return ids
