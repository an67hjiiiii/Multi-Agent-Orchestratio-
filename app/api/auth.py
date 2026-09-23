from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from fastapi import APIRouter, Depends, Response

from app.api.dependencies import (
    get_auth_store,
    get_current_user,
    get_session_token,
)
from app.api.errors import ApiError
from app.api.schemas import AuthLoginRequest, AuthRegisterRequest
from app.auth.store import (
    AuthStore,
    DuplicateUserError,
    InvalidCredentialsError,
    InvalidSessionError,
)


router = APIRouter()


def auth_error(code: str, message: str, status_code: int = 400) -> ApiError:
    return ApiError(status_code, code, message)


def auth_payload(
    *,
    user: Mapping[str, Any],
    session: Mapping[str, Any],
    access_token: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "authenticated": True,
        "user": dict(user),
        "session": dict(session),
        "token_type": "bearer",
    }
    if access_token is not None:
        # Raw tokens are returned only at login/register boundaries.
        payload["access_token"] = access_token
        payload["token"] = access_token
    return payload


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        "session_token",
        token,
        httponly=True,
        secure=False,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie("session_token", path="/")
    response.delete_cookie("local_session", path="/")


def login_identifier(body: AuthLoginRequest) -> str:
    for value in (body.identifier, body.email, body.username):
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise auth_error("IDENTIFIER_REQUIRED", "email, username, or identifier is required")


@router.post("/auth/register")
def register(
    body: AuthRegisterRequest,
    response: Response,
    store: AuthStore = Depends(get_auth_store),
) -> dict[str, Any]:
    try:
        user = store.register(
            email=body.email,
            username=body.username,
            display_name=body.display_name or body.name,
            password=body.password,
            role=body.role,
        )
        token, session = store.create_session(str(user["user_id"]))
    except DuplicateUserError as exc:
        raise auth_error("ACCOUNT_EXISTS", str(exc), 409) from exc
    except ValueError as exc:
        raise auth_error("INVALID_REGISTRATION", str(exc)) from exc

    set_session_cookie(response, token)
    return auth_payload(user=user, session=session, access_token=token)


@router.post("/auth/login")
def login(
    body: AuthLoginRequest,
    response: Response,
    store: AuthStore = Depends(get_auth_store),
) -> dict[str, Any]:
    try:
        user, token, session = store.authenticate(
            identifier=login_identifier(body),
            password=body.password,
        )
    except InvalidCredentialsError as exc:
        raise auth_error("INVALID_CREDENTIALS", "Invalid email, username, or password", 401) from exc
    except ValueError as exc:
        raise auth_error("INVALID_LOGIN", str(exc)) from exc

    set_session_cookie(response, token)
    return auth_payload(user=user, session=session, access_token=token)


@router.post("/auth/logout")
def logout(
    response: Response,
    token: str | None = Depends(get_session_token),
    store: AuthStore = Depends(get_auth_store),
) -> dict[str, Any]:
    store.revoke(token)
    clear_session_cookie(response)
    return {"ok": True, "authenticated": False}


@router.get("/auth/session")
def auth_session(
    token: str | None = Depends(get_session_token),
    store: AuthStore = Depends(get_auth_store),
) -> dict[str, Any]:
    if not token:
        return {"authenticated": False, "user": None, "session": None, "token_type": "bearer"}
    try:
        user = store.resolve(token)
    except InvalidSessionError:
        return {"authenticated": False, "user": None, "session": None, "token_type": "bearer"}
    session = store.session_for_token(token)
    if session is None:
        return {"authenticated": False, "user": None, "session": None, "token_type": "bearer"}
    return auth_payload(user=user, session=session)


@router.get("/auth/me")
def auth_me(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return {"authenticated": True, "user": user}
