from __future__ import annotations
import os
from app.providers.fake import FakeProvider
from app.providers.ollama import OllamaProvider


def get_provider(name: str | None = None):
    provider = (name or os.getenv("PROVIDER", "fake")).strip().lower()
    if provider == "fake":
        return FakeProvider()
    if provider in {"ollama", "local"}:
        return OllamaProvider()
    raise ValueError("Only fake and local Ollama providers are allowed in the clean research build")
