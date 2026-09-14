from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


try:
    from app.research.task_schema import DecompositionResult
except ModuleNotFoundError as exc:
    # The task-schema worker is integrated separately from this API worker.
    if exc.name != "app.research.task_schema":
        raise
    DecompositionResult: Any = None


DECOMPOSITION_RESPONSE_MODEL = DecompositionResult


class ChatRequest(BaseModel):
    message: str
    condition: str = "A"
    provider: str | None = None


class ConversationCreateRequest(BaseModel):
    title: str | None = None


class ConversationMessageRequest(BaseModel):
    message: str
    condition: str = "A"
    provider: str | None = None


class SourceTextRequest(BaseModel):
    source_name: str
    text: str


class AuthRegisterRequest(BaseModel):
    """Local account registration input.

    ``username`` is optional so existing email-first callers can register,
    while ``email`` is optional for a local username-only workspace.  The
    backend assigns ADMIN only for an explicit first-account bootstrap;
    later self-registration is always USER.
    """

    email: str | None = None
    username: str | None = None
    name: str | None = None
    display_name: str | None = None
    password: str
    role: str = "USER"


class AuthLoginRequest(BaseModel):
    """Identifier/password input for the local session boundary."""

    email: str | None = None
    username: str | None = None
    identifier: str | None = None
    password: str


class AuthUserDTO(BaseModel):
    """Safe public user shape; no password or token material is exposed."""

    id: str
    user_id: str
    email: str | None = None
    username: str | None = None
    name: str = ""
    display_name: str = ""
    role: str
    created_at: str | None = None
    updated_at: str | None = None
    last_login_at: str | None = None
    status: str = "ACTIVE"


class AuthSessionDTO(BaseModel):
    session_id: str
    user_id: str
    created_at: str
    expires_at: str


class AuthResponseDTO(BaseModel):
    authenticated: bool = True
    user: AuthUserDTO
    session: AuthSessionDTO
    access_token: str | None = None
    token_type: str = "bearer"


class SourceChunkDTO(BaseModel):
    chunk_id: str
    source_id: str
    source_name: str
    text: str
    index: int
    score: float | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)


class SourceSummaryDTO(BaseModel):
    source_id: str
    source_name: str
    chunk_count: int = 0
    source_type: str | None = None
    source_format: str | None = None
    index_status: str | None = None


class SourceDetailDTO(BaseModel):
    source_id: str
    source_name: str
    chunks: list[SourceChunkDTO] = Field(default_factory=list)


class RunHistoryItemDTO(BaseModel):
    run_id: str
    created_at: str | None = None
    condition: str | None = None
    query: str | None = None
    status: str | None = None


class RunTraceDTO(BaseModel):
    run_id: str
    status: str | None = None
    events: list[dict[str, Any]] = Field(default_factory=list)
    trace: list[dict[str, Any]] = Field(default_factory=list)
    effective_config: dict[str, Any] | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)


class RunEvidenceDTO(BaseModel):
    run_id: str
    source_snapshot_id: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    items: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    missing_ids: list[str] = Field(default_factory=list)


class DecompositionRequest(BaseModel):
    """Input for the inspection-only P-lite decomposition boundary."""

    request: str
    provider: str | None = None


# Keep the feature name available to callers that describe this as a planning
# request while retaining one request model and one wire shape.
PlanningRequest = DecompositionRequest
