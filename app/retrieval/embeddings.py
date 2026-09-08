from __future__ import annotations

import hashlib
import math
import os
from dataclasses import dataclass
from ipaddress import ip_address
from typing import Protocol
from urllib.parse import urlsplit

import httpx

from app.retrieval.text import normalize_text, terms


EMBEDDING_VERSION = "local-hash-embedding-v1"
OLLAMA_EMBEDDING_VERSION = "ollama-embedding-v1"


class TextEmbedder(Protocol):
    dimension: int
    version: str

    def embed(self, text: str) -> tuple[float, ...]: ...


@dataclass(frozen=True)
class LocalHashEmbedder:
    """Dependency-free local vectorizer for the optional vector boundary.

    This is a deterministic lexical/hash embedding, not a semantic model.  It
    keeps the Qdrant/InMemory path usable without downloading a new model and
    records its version so it cannot be confused with frozen research
    embeddings.
    """

    dimension: int = 768
    version: str = EMBEDDING_VERSION

    def __post_init__(self) -> None:
        if isinstance(self.dimension, bool) or not isinstance(self.dimension, int):
            raise TypeError("embedding dimension must be an integer")
        if self.dimension < 1:
            raise ValueError("embedding dimension must be positive")

    def embed(self, text: str) -> tuple[float, ...]:
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        clean = normalize_text(text)
        vector = [0.0] * self.dimension
        token_values = sorted(terms(clean))
        if not token_values and clean:
            token_values = [clean.casefold()]

        for token in token_values:
            digest = hashlib.sha256(
                f"{self.version}\0{token}".encode("utf-8")
            ).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0.0:
            return tuple(vector)
        return tuple(round(value / norm, 8) for value in vector)


class EmbeddingBackendUnavailable(RuntimeError):
    """Raised when the explicitly selected local embedding backend is unavailable."""


class OllamaEmbedder:
    """Synchronous local Ollama embedding boundary for indexing/search.

    The adapter is opt-in through ``EMBEDDING_PROVIDER=ollama``. Keeping the
    default hash embedder preserves deterministic offline tests and the lexical
    last-known-good path.
    """

    def __init__(
        self,
        *,
        model: str | None = None,
        base_url: str | None = None,
        dimension: int = 768,
        timeout: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.model = (model or os.getenv("LOCAL_EMBEDDING_MODEL", "nomic-embed-text")).strip()
        if not self.model or any(character.isspace() for character in self.model):
            raise ValueError("LOCAL_EMBEDDING_MODEL must be a non-empty model tag")
        self.base_url = self._validate_base_url(
            base_url or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        )
        if isinstance(dimension, bool) or not isinstance(dimension, int) or dimension < 1:
            raise ValueError("embedding dimension must be positive")
        if not math.isfinite(float(timeout)) or timeout <= 0:
            raise ValueError("embedding timeout must be positive")
        self.dimension = dimension
        self.version = f"{OLLAMA_EMBEDDING_VERSION}:{self.model}"
        self._client = client
        self.timeout = float(timeout)

    def embed(self, text: str) -> tuple[float, ...]:
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        payload = {"model": self.model, "input": text}
        try:
            if self._client is not None:
                response = self._client.post(
                    f"{self.base_url}/api/embed", json=payload, timeout=self.timeout
                )
            else:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(f"{self.base_url}/api/embed", json=payload)
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise EmbeddingBackendUnavailable(
                "Local Ollama embedding request failed"
            ) from exc

        values = data.get("embeddings") if isinstance(data, dict) else None
        if isinstance(values, list) and values and isinstance(values[0], list):
            values = values[0]
        if values is None and isinstance(data, dict):
            values = data.get("embedding")
        if not isinstance(values, list) or not values:
            raise EmbeddingBackendUnavailable("Ollama returned no embedding vector")
        try:
            vector = tuple(float(value) for value in values)
        except (TypeError, ValueError) as exc:
            raise EmbeddingBackendUnavailable("Ollama returned an invalid embedding vector") from exc
        if len(vector) != self.dimension:
            raise EmbeddingBackendUnavailable(
                f"Ollama embedding dimension {len(vector)} does not match configured {self.dimension}"
            )
        if not all(math.isfinite(value) for value in vector):
            raise EmbeddingBackendUnavailable("Ollama returned non-finite embedding values")
        return vector

    @staticmethod
    def _validate_base_url(value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("OLLAMA_BASE_URL must be a local HTTP(S) URL")
        raw = value.strip()
        parsed = urlsplit(raw)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("OLLAMA_BASE_URL must be a local HTTP(S) URL")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("OLLAMA_BASE_URL must not contain credentials or query data")
        hostname = (parsed.hostname or "").casefold().rstrip(".")
        try:
            local = hostname == "localhost" or ip_address(hostname).is_loopback
        except ValueError:
            local = False
        if not local:
            raise ValueError("OLLAMA_BASE_URL must point to loopback")
        return raw.rstrip("/")


__all__ = [
    "EMBEDDING_VERSION",
    "EmbeddingBackendUnavailable",
    "LocalHashEmbedder",
    "OLLAMA_EMBEDDING_VERSION",
    "OllamaEmbedder",
    "TextEmbedder",
]
