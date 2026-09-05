from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from app.core.config import RuntimeConfig
from app.providers.ollama import OllamaProvider
from app.research.pipeline import ResearchPipeline
from app.storage.run_store import RunStore
from app.storage.source_store import SourceStore

BASE = Path(__file__).resolve().parent.parent
load_dotenv(BASE / ".env", override=False)
DATA_DIR = os.getenv("APP_DATA_DIR", str(BASE / "data"))
RUNS_DIR = os.getenv("RUNS_DIR", str(BASE / "runs"))

app = FastAPI(title="Local Multi-Agent RAG", version="0.2.0-m0")
app.mount("/static", StaticFiles(directory=BASE / "app" / "static"), name="static")
source_store = SourceStore(DATA_DIR)
run_store = RunStore(RUNS_DIR)
pipeline = ResearchPipeline(source_store, run_store)

class ChatRequest(BaseModel):
    message: str
    condition: str = "A"
    provider: str | None = None

class SourceTextRequest(BaseModel):
    source_name: str
    text: str

@app.get("/")
def index():
    return FileResponse(BASE / "app" / "static" / "index.html")

@app.get("/api/health")
def health():
    cfg = RuntimeConfig.from_env()
    return {
        "ok": True,
        "app": "local-multi-agent-rag",
        "version": "0.2.0-m0",
        "implementation_profile": cfg.implementation_profile,
        "allowed_conditions": cfg.allowed_conditions(),
        "default_provider": os.getenv("PROVIDER", "fake"),
        "source_snapshot_id": source_store.snapshot_id(),
        "config_hash": cfg.config_hash(),
    }

@app.get("/api/config")
def config():
    cfg = RuntimeConfig.from_env()
    return {**cfg.public_dict(), "allowed_conditions": cfg.allowed_conditions(), "config_hash": cfg.config_hash()}

@app.get("/api/local-model/health")
async def local_model_health():
    try:
        return await OllamaProvider().health()
    except Exception as exc:
        return {"ok": False, "error": str(exc), "configured_model": os.getenv("LOCAL_LLM_MODEL", "qwen3:4b")}

@app.get("/api/sources")
def list_sources():
    return {"snapshot_id": source_store.snapshot_id(), "sources": source_store.list_sources()}

@app.get("/api/sources/{source_id}")
def get_source(source_id: str):
    item = source_store.source(source_id)
    if not item:
        raise HTTPException(404, "source not found")
    return item

@app.get("/api/chunks/{chunk_id}")
def get_chunk(chunk_id: str):
    item = source_store.chunk(chunk_id)
    if not item:
        raise HTTPException(404, "chunk not found")
    return item

@app.post("/api/sources/text")
def import_text(body: SourceTextRequest):
    if not body.text.strip():
        raise HTTPException(400, "text is empty")
    return source_store.import_text(body.source_name, body.text)

@app.post("/api/sources/file")
async def import_file(file: UploadFile = File(...)):
    data = await file.read()
    if len(data) > 2_000_000:
        raise HTTPException(413, "M0 only accepts UTF-8 text/code/markdown files up to 2 MB")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(415, "M0 accepts UTF-8 text/code/markdown files only")
    if not text.strip():
        raise HTTPException(400, "file is empty")
    return source_store.import_text(file.filename or "upload.txt", text)

@app.post("/api/chat")
async def chat(body: ChatRequest):
    if not body.message.strip():
        raise HTTPException(400, "message is required")
    try:
        run = await pipeline.run(body.message.strip(), body.condition, body.provider)
        if run["status"] == "FAILED":
            return run
        return run
    except ValueError as exc:
        raise HTTPException(400, str(exc))

@app.get("/api/runs")
def list_runs():
    return run_store.list()

@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    run = run_store.get(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    return run
