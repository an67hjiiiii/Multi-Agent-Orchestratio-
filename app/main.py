from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.errors import register_exception_handlers
from app.api.router import router as api_router
from app.core.api_runtime import ApiRuntime

BASE = Path(__file__).resolve().parent.parent


def create_app(
    *,
    data_dir: str | Path | None = None,
    runs_dir: str | Path | None = None,
) -> FastAPI:
    """Build an isolated API plus the legacy static frontend boundary."""

    application = FastAPI(title="Local Multi-Agent RAG", version="0.2.0-m0")
    register_exception_handlers(application)
    application.state.api_runtime = ApiRuntime.from_env(
        data_dir=data_dir,
        runs_dir=runs_dir,
    )
    application.include_router(api_router)
    application.mount(
        "/static",
        StaticFiles(directory=BASE / "app" / "static"),
        name="static",
    )

    @application.get("/")
    def index():
        return FileResponse(BASE / "app" / "static" / "index.html")

    return application


app = create_app()
