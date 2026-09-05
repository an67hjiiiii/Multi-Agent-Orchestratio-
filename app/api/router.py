from __future__ import annotations

import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.dependencies import get_api_runtime
from app.api.schemas import ChatRequest, SourceTextRequest
from app.core.api_runtime import ApiRuntime
from app.core.config import RuntimeConfig
from app.providers.ollama import OllamaProvider


router = APIRouter(prefix="/api")


@router.get("/health")
def health(runtime: ApiRuntime = Depends(get_api_runtime)):
    cfg = RuntimeConfig.from_env()
    return {
        "ok": True,
        "app": "local-multi-agent-rag",
        "version": "0.2.0-m0",
        "implementation_profile": cfg.implementation_profile,
        "allowed_conditions": cfg.allowed_conditions(),
        "default_provider": os.getenv("PROVIDER", "fake"),
        "source_snapshot_id": runtime.source_store.snapshot_id(),
        "config_hash": cfg.config_hash(),
    }


@router.get("/config")
def config():
    cfg = RuntimeConfig.from_env()
    return {
        **cfg.public_dict(),
        "allowed_conditions": cfg.allowed_conditions(),
        "config_hash": cfg.config_hash(),
    }


@router.get("/local-model/health")
async def local_model_health():
    try:
        return await OllamaProvider().health()
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "configured_model": os.getenv("LOCAL_LLM_MODEL", "qwen3:4b"),
        }


@router.get("/sources")
def list_sources(runtime: ApiRuntime = Depends(get_api_runtime)):
    return {
        "snapshot_id": runtime.source_store.snapshot_id(),
        "sources": runtime.source_store.list_sources(),
    }


@router.get("/sources/{source_id}")
def get_source(source_id: str, runtime: ApiRuntime = Depends(get_api_runtime)):
    item = runtime.source_store.source(source_id)
    if not item:
        raise HTTPException(404, "source not found")
    return item


@router.get("/chunks/{chunk_id}")
def get_chunk(chunk_id: str, runtime: ApiRuntime = Depends(get_api_runtime)):
    item = runtime.source_store.chunk(chunk_id)
    if not item:
        raise HTTPException(404, "chunk not found")
    return item


@router.post("/sources/text")
def import_text(
    body: SourceTextRequest,
    runtime: ApiRuntime = Depends(get_api_runtime),
):
    if not body.text.strip():
        raise HTTPException(400, "text is empty")
    return runtime.source_store.import_text(body.source_name, body.text)


@router.post("/sources/file")
async def import_file(
    file: UploadFile = File(...),
    runtime: ApiRuntime = Depends(get_api_runtime),
):
    data = await file.read()
    if len(data) > 2_000_000:
        raise HTTPException(413, "M0 only accepts UTF-8 text/code/markdown files up to 2 MB")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(415, "M0 accepts UTF-8 text/code/markdown files only")
    if not text.strip():
        raise HTTPException(400, "file is empty")
    return runtime.source_store.import_text(file.filename or "upload.txt", text)


@router.post("/chat")
async def chat(
    body: ChatRequest,
    runtime: ApiRuntime = Depends(get_api_runtime),
):
    if not body.message.strip():
        raise HTTPException(400, "message is required")
    try:
        run = await runtime.pipeline.run(body.message.strip(), body.condition, body.provider)
        if run["status"] == "FAILED":
            return run
        return run
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.get("/runs")
def list_runs(runtime: ApiRuntime = Depends(get_api_runtime)):
    return runtime.run_store.list()


@router.get("/runs/{run_id}")
def get_run(run_id: str, runtime: ApiRuntime = Depends(get_api_runtime)):
    run = runtime.run_store.get(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    return run
