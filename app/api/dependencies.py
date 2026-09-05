from __future__ import annotations

from fastapi import Request

from app.core.api_runtime import ApiRuntime


def get_api_runtime(request: Request) -> ApiRuntime:
    """Return the runtime installed by ``create_app``."""

    return request.app.state.api_runtime
