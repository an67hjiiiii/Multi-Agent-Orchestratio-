from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(StarletteHTTPException):
    """An HTTP error with a stable, additive public error contract."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        detail: Any | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.retryable = retryable
        super().__init__(status_code=status_code, detail=message if detail is None else detail)


def error_payload(
    *,
    detail: Any,
    code: str,
    message: str,
    retryable: bool,
) -> dict[str, Any]:
    """Return an additive payload while retaining FastAPI's legacy detail key."""

    return {
        "detail": detail,
        "code": code,
        "message": message,
        "retryable": retryable,
    }


def _code_for_status(status_code: int) -> str:
    return {
        400: "BAD_REQUEST",
        404: "NOT_FOUND",
        413: "PAYLOAD_TOO_LARGE",
        415: "UNSUPPORTED_MEDIA_TYPE",
        422: "VALIDATION_ERROR",
        500: "INTERNAL_ERROR",
        502: "UPSTREAM_ERROR",
        503: "SERVICE_UNAVAILABLE",
    }.get(status_code, "HTTP_ERROR")


def _message_for_detail(detail: Any, status_code: int) -> str:
    if isinstance(detail, str) and detail:
        return detail
    if status_code == 422:
        return "Request validation failed"
    return "Request failed"


async def api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(
            detail=exc.detail,
            code=exc.code,
            message=exc.message,
            retryable=exc.retryable,
        ),
    )


async def http_error_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(
            detail=jsonable_encoder(exc.detail),
            code=_code_for_status(exc.status_code),
            message=_message_for_detail(exc.detail, exc.status_code),
            retryable=exc.status_code in {502, 503, 504},
        ),
    )


async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    details = jsonable_encoder(exc.errors())
    return JSONResponse(
        status_code=422,
        content=error_payload(
            detail=details,
            code="VALIDATION_ERROR",
            message="Request validation failed",
            retryable=False,
        ),
    )


async def internal_error_handler(_request: Request, _exc: Exception) -> JSONResponse:
    """Do not expose provider, filesystem, or configuration exception text."""

    return JSONResponse(
        status_code=500,
        content=error_payload(
            detail="Internal server error",
            code="INTERNAL_ERROR",
            message="Internal server error",
            retryable=False,
        ),
    )


def register_exception_handlers(application: FastAPI) -> None:
    application.add_exception_handler(ApiError, api_error_handler)
    application.add_exception_handler(RequestValidationError, validation_error_handler)
    application.add_exception_handler(StarletteHTTPException, http_error_handler)
    application.add_exception_handler(Exception, internal_error_handler)
