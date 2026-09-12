from __future__ import annotations

from pathlib import Path

from fastapi import Request

from app.auth.store import AuthStore, InvalidSessionError
from app.core.api_runtime import ApiRuntime
from app.api.errors import ApiError


def get_api_runtime(request: Request) -> ApiRuntime:
    """Return the runtime installed by ``create_app``."""

    return request.app.state.api_runtime


def get_auth_store(request: Request) -> AuthStore:
    """Return the app-scoped local auth store for the runtime data root.

    Authentication is deliberately lazy so existing API-only callers keep the
    same startup path and test applications do not need a second runtime
    constructor argument.  The store is cached on the FastAPI app instance,
    while its JSON file remains restart-persistent under the runtime data
    directory.
    """

    runtime = get_api_runtime(request)
    data_root = Path(runtime.source_store.root)
    store = getattr(request.app.state, "auth_store", None)
    if not isinstance(store, AuthStore) or store.root != data_root:
        store = AuthStore(data_root)
        request.app.state.auth_store = store
    return store


def _session_token(request: Request) -> str | None:
    """Read the local bearer token without accepting query-string secrets."""

    authorization = request.headers.get("authorization", "").strip()
    if authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
        if token:
            return token
    header_token = request.headers.get("x-session-token", "").strip()
    if header_token:
        return header_token
    for cookie_name in ("session_token", "local_session"):
        token = request.cookies.get(cookie_name, "").strip()
        if token:
            return token
    return None


def get_session_token(request: Request) -> str | None:
    """Expose the normalized token to API routes that need optional auth."""

    return _session_token(request)


def get_current_user(
    request: Request,
) -> dict:
    """Resolve the authenticated local user or return a safe 401 error."""

    resolved_store = get_auth_store(request)
    try:
        return resolved_store.resolve(_session_token(request))
    except InvalidSessionError as exc:
        raise ApiError(
            401,
            "AUTHENTICATION_REQUIRED",
            "Authentication is required",
        ) from exc


def get_admin_user(request: Request) -> dict:
    """Resolve an authenticated ADMIN user for management endpoints."""

    user = get_current_user(request)
    if str(user.get("role") or "").upper() != "ADMIN":
        raise ApiError(403, "ADMIN_REQUIRED", "Administrator access is required")
    return user
