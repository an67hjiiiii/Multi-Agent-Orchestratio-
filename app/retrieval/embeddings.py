from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Protocol

from app.retrieval.text import normalize_text, terms


EMBEDDING_VERSION = "local-hash-embedding-v1"


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


__all__ = ["EMBEDDING_VERSION", "LocalHashEmbedder", "TextEmbedder"]
