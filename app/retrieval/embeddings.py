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
    """Deterministic local vectorizer for the optional derived index.

    This is a lexical/hash embedding, not a research model.  It keeps local
    index tests deterministic and records a version so it cannot be confused
    with semantic-model evidence.
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
        values = [0.0] * self.dimension
        tokens = sorted(terms(clean))
        if not tokens and clean:
            tokens = [clean.casefold()]
        for token in tokens:
            digest = hashlib.sha256(
                f"{self.version}\0{token}".encode("utf-8")
            ).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            values[index] += 1.0 if digest[4] & 1 else -1.0
        norm = math.sqrt(sum(value * value for value in values))
        if norm == 0.0:
            return tuple(values)
        return tuple(round(value / norm, 8) for value in values)


__all__ = ["EMBEDDING_VERSION", "LocalHashEmbedder", "TextEmbedder"]
