from __future__ import annotations

from typing import Any

from pydantic import BaseModel


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


class SourceTextRequest(BaseModel):
    source_name: str
    text: str


class DecompositionRequest(BaseModel):
    """Input for the inspection-only P-lite decomposition boundary."""

    request: str
    provider: str | None = None


# Keep the feature name available to callers that describe this as a planning
# request while retaining one request model and one wire shape.
PlanningRequest = DecompositionRequest
