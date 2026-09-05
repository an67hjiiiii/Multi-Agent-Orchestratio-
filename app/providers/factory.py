from __future__ import annotations

import os

from app.providers.base import Provider
from app.providers.fake import FakeProvider
from app.providers.ollama import OllamaProvider


ALLOWED_PROVIDER_IDS = frozenset({"fake", "ollama", "local"})


def get_provider(name: str | None = None) -> Provider:
    configured = os.getenv("PROVIDER", "fake") if name is None else name
    if not isinstance(configured, str) or not configured.strip():
        raise ValueError("A provider is required; only fake and local Ollama are allowed")

    provider = configured.strip().lower()
    if provider not in ALLOWED_PROVIDER_IDS:
        raise ValueError("Only fake and local Ollama providers are allowed in the clean research build")
    if provider == "fake":
        return FakeProvider()
    return OllamaProvider()
