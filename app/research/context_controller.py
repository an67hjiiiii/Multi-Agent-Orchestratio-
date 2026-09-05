from __future__ import annotations
import hashlib
from app.core.types import SourceChunk

class ContextController:
    def __init__(self, max_chars: int = 5000):
        self.max_chars = max_chars

    def select(self, candidates: list[SourceChunk]) -> tuple[list[SourceChunk], list[dict]]:
        selected: list[SourceChunk] = []
        dropped: list[dict] = []
        seen_exact: set[str] = set()
        used = 0
        for chunk in sorted(candidates, key=lambda c: (-c.score, c.chunk_id)):
            digest = hashlib.sha256(chunk.text.strip().encode()).hexdigest()
            if digest in seen_exact:
                dropped.append({"chunk_id": chunk.chunk_id, "reason": "exact_duplicate"})
                continue
            if used + len(chunk.text) > self.max_chars:
                dropped.append({"chunk_id": chunk.chunk_id, "reason": "token_budget_proxy"})
                continue
            seen_exact.add(digest)
            selected.append(chunk)
            used += len(chunk.text)
        return selected, dropped
