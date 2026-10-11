from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from app.api.auth import router as auth_router
from app.api.auth import get_session_token
from app.auth.store import AuthStore, InvalidSessionError
from app.core.config import RuntimeConfig
from app.ingestion.documents import DocumentTypeError, extract_document
from app.providers.ollama import OllamaProvider
from app.research.pipeline import ResearchPipeline
from app.storage.run_store import RunStore
from app.storage.source_store import SourceStore
from app.storage.conversation_store import ConversationStore
from app.storage.postgres import create_postgres_engine, create_session_factory
from app.storage.postgres.config import PostgresConfigurationError
from app.storage.postgres.runtime import (
    PostgresAuthStore,
    PostgresConversationStore,
    PostgresRunStore,
    PostgresSourceStore,
)

BASE = Path(__file__).resolve().parent.parent
load_dotenv(BASE / ".env", override=False)
DATA_DIR = os.getenv("APP_DATA_DIR", str(BASE / "data"))
RUNS_DIR = os.getenv("RUNS_DIR", str(BASE / "runs"))
STORAGE_BACKEND = os.getenv("APP_STORAGE_BACKEND", "postgres").strip().lower()


def _configured_stores(storage_backend: str | None = None):
    backend = (storage_backend or os.getenv("APP_STORAGE_BACKEND", "postgres")).strip().lower()
    if backend == "file":
        return AuthStore(DATA_DIR), SourceStore(DATA_DIR), RunStore(RUNS_DIR), None
    if backend != "postgres":
        raise PostgresConfigurationError("APP_STORAGE_BACKEND must be postgres or file")
    engine = create_postgres_engine()
    session_factory = create_session_factory(engine)
    return PostgresAuthStore(session_factory), None, None, (engine, session_factory)

app = FastAPI(title="Local Multi-Agent RAG", version="0.2.0-m0")
app.mount("/static", StaticFiles(directory=BASE / "app" / "static"), name="static")
app.include_router(auth_router)
auth_store, source_store, run_store, postgres_runtime = _configured_stores()
app.state.storage_backend = STORAGE_BACKEND
app.state.auth_store = auth_store
app.state.session_factory = None if postgres_runtime is None else postgres_runtime[1]
pipeline = None if STORAGE_BACKEND == "postgres" else ResearchPipeline(source_store, run_store)

def current_user(request: Request) -> dict:
    try:
        return request.app.state.auth_store.resolve(get_session_token(request))
    except InvalidSessionError as exc:
        raise HTTPException(status_code=401, detail="Authentication is required") from exc

def owner_source_store(user: dict):
    if STORAGE_BACKEND == "postgres":
        return PostgresSourceStore(app.state.session_factory, str(user["user_id"]))
    root = Path(DATA_DIR) / "owners" / str(user["user_id"]) / "sources"
    return SourceStore(str(root))

def owner_run_store(user: dict, conversation_id: str | None = None):
    if STORAGE_BACKEND == "postgres":
        return PostgresRunStore(
            app.state.session_factory, str(user["user_id"]), conversation_id
        )
    root = Path(RUNS_DIR) / "owners" / str(user["user_id"])
    return RunStore(str(root))

def owner_pipeline(user: dict, conversation_id: str | None = None) -> ResearchPipeline:
    return ResearchPipeline(owner_source_store(user), owner_run_store(user, conversation_id))


def owner_conversation_store(user: dict):
    if STORAGE_BACKEND == "postgres":
        return PostgresConversationStore(app.state.session_factory, str(user["user_id"]))
    root = Path(DATA_DIR) / "owners" / str(user["user_id"]) / "conversations"
    return ConversationStore(root)

class ChatRequest(BaseModel):
    message: str
    condition: str = "A"
    provider: str | None = None
    conversation_id: str | None = None

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
        "source_snapshot_id": None if source_store is None else source_store.snapshot_id(),
        "storage_backend": STORAGE_BACKEND,
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
def list_sources(request: Request):
    user = current_user(request)
    store = owner_source_store(user)
    return {"snapshot_id": store.snapshot_id(), "sources": store.list_sources()}

@app.get("/api/sources/{source_id}")
def get_source(source_id: str, request: Request):
    item = owner_source_store(current_user(request)).source(source_id)
    if not item:
        raise HTTPException(404, "source not found")
    return item

@app.get("/api/chunks/{chunk_id}")
def get_chunk(chunk_id: str, request: Request):
    item = owner_source_store(current_user(request)).chunk(chunk_id)
    if not item:
        raise HTTPException(404, "chunk not found")
    return item

@app.post("/api/sources/text")
def import_text(body: SourceTextRequest, request: Request):
    if not body.text.strip():
        raise HTTPException(400, "text is empty")
    return owner_source_store(current_user(request)).import_text(body.source_name, body.text)

@app.post("/api/sources/file")
async def import_file(request: Request, file: UploadFile = File(...)):
    user = current_user(request)
    data = await file.read()
    if len(data) > 2_000_000:
        raise HTTPException(413, "Files must be no larger than 2 MB")

    source_name = file.filename or "upload.txt"
    try:
        document = extract_document(
            data,
            source_name,
            origin="upload",
            content_type=file.content_type,
        )
    except DocumentTypeError as exc:
        detail = (
            "PDF_NO_TEXT"
            if "no extractable text" in str(exc)
            else "PDF_EXTRACTION_UNAVAILABLE"
        )
        if not source_name.lower().endswith(".pdf"):
            detail = "UNSUPPORTED_DOCUMENT_TYPE"
        raise HTTPException(415 if detail != "PDF_NO_TEXT" else 422, detail) from exc
    except UnicodeError as exc:
        raise HTTPException(415, "UTF8_TEXT_REQUIRED") from exc
    except ValueError as exc:
        if "must not be empty" in str(exc):
            raise HTTPException(400, "file is empty") from exc
        raise HTTPException(415, "DOCUMENT_EXTRACTION_FAILED") from exc
    return owner_source_store(user).import_text(document.source_name, document.text)

@app.post("/api/chat")
async def chat(body: ChatRequest, request: Request):
    if not body.message.strip():
        raise HTTPException(400, "message is required")
    try:
        user = current_user(request)
        RuntimeConfig.from_env().assert_condition(body.condition.upper())
        conversations = owner_conversation_store(user)
        if body.conversation_id:
            if conversations.get(body.conversation_id) is None:
                raise HTTPException(404, "conversation not found")
            conversation_id = body.conversation_id
        else:
            conversation_id = conversations.create(body.message.strip()[:120])["conversation_id"]
        conversations.add_message(conversation_id, "USER", body.message.strip())
        run = await owner_pipeline(user, conversation_id).run(
            body.message.strip(), body.condition, body.provider
        )
        conversations.add_message(
            conversation_id,
            "ASSISTANT",
            str(run.get("answer") or run.get("status") or "Run completed"),
            run_id=run["run_id"],
        )
        run = {**run, "conversation_id": conversation_id}
        if run["status"] == "FAILED":
            return run
        return run
    except ValueError as exc:
        raise HTTPException(400, str(exc))

@app.get("/api/runs")
def list_runs(request: Request):
    return owner_run_store(current_user(request)).list()

@app.get("/api/runs/{run_id}")
def get_run(run_id: str, request: Request):
    run = owner_run_store(current_user(request)).get(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    return run


@app.get("/api/conversations")
def list_conversations(request: Request):
    return owner_conversation_store(current_user(request)).list()


@app.get("/api/conversations/{conversation_id}")
def get_conversation(conversation_id: str, request: Request):
    conversation = owner_conversation_store(current_user(request)).get(conversation_id)
    if conversation is None:
        raise HTTPException(404, "conversation not found")
    return conversation
