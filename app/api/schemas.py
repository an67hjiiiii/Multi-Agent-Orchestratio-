from __future__ import annotations

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    condition: str = "A"
    provider: str | None = None


class SourceTextRequest(BaseModel):
    source_name: str
    text: str
