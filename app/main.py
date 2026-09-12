from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.datastructures import Headers
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.staticfiles import NotModifiedResponse
from starlette.types import Scope

from app.api.errors import ApiError, register_exception_handlers
from app.api.router import router as api_router
from app.core.api_runtime import ApiRuntime

BASE = Path(__file__).resolve().parent.parent
FRONTEND_DIST = BASE / "frontend" / "dist"
LEGACY_STATIC = BASE / "app" / "static"
API_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]


class SPAStaticFiles(StaticFiles):
    """Serve Vite assets and return the app shell for client-side routes."""

    _MEDIA_TYPES = {
        ".js": "text/javascript",
        ".mjs": "text/javascript",
    }

    def __init__(self, *, index_path: str | Path, **kwargs: Any) -> None:
        self.index_path = Path(index_path)
        super().__init__(**kwargs)

    def file_response(self, full_path, stat_result, scope, status_code=200):
        """Serve module assets with a browser-compatible JavaScript MIME type."""

        request_headers = Headers(scope=scope)
        suffix = Path(full_path).suffix.lower()
        response = FileResponse(
            full_path,
            status_code=status_code,
            stat_result=stat_result,
            media_type=self._MEDIA_TYPES.get(suffix),
        )
        if self.is_not_modified(response.headers, request_headers):
            return NotModifiedResponse(response.headers)
        return response

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            response = await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404:
                raise
            return FileResponse(self.index_path)

        if response.status_code == 404:
            return FileResponse(self.index_path)
        return response


def create_app(
    *,
    data_dir: str | Path | None = None,
    runs_dir: str | Path | None = None,
    frontend_dist_dir: str | Path | None = None,
) -> FastAPI:
    """Build an isolated API plus the Vite production frontend boundary."""

    application = FastAPI(title="Local Multi-Agent RAG", version="0.2.0-m0")
    register_exception_handlers(application)
    application.state.api_runtime = ApiRuntime.from_env(
        data_dir=data_dir,
        runs_dir=runs_dir,
    )
    application.include_router(api_router)

    def api_not_found() -> None:
        raise ApiError(404, "NOT_FOUND", "API route not found")

    # Keep the root SPA mount from turning an unknown API request into HTML.
    for path in ("/api", "/api/{path:path}"):
        application.add_api_route(
            path,
            api_not_found,
            methods=API_METHODS,
            include_in_schema=False,
        )

    application.mount(
        "/static",
        StaticFiles(directory=LEGACY_STATIC),
        name="static",
    )

    frontend_dist = Path(frontend_dist_dir) if frontend_dist_dir is not None else FRONTEND_DIST
    frontend_index = frontend_dist / "index.html"
    if frontend_index.is_file():
        application.mount(
            "/",
            SPAStaticFiles(
                directory=frontend_dist,
                html=True,
                index_path=frontend_index,
            ),
            name="frontend",
        )
    else:

        @application.get("/", include_in_schema=False)
        def frontend_unavailable():
            return PlainTextResponse(
                "Frontend build is unavailable; run `npm --prefix frontend run build`.",
                status_code=503,
            )

    return application


app = create_app()
