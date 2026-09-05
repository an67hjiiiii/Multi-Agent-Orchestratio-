from __future__ import annotations
import hashlib
from app.core.types import SourceChunk
from app.retrieval.text import estimate_tokens, normalize_text

class ContextController:
    """Select deterministic evidence without exceeding a configured budget.

    ``max_chars`` remains the legacy character-budget mode used by the
    pre-M1 controller.  M0 callers should use ``max_tokens`` or
    ``select_with_token_budget`` so the hard pre-call cap is measured with the
    same conservative token proxy as retrieval.
    """

    def __init__(self, max_chars: int = 5000, *, max_tokens: int | None = None):
        self.max_chars = self._validate_budget(max_chars, "max_chars")
        self.max_tokens = (
            None if max_tokens is None else self._validate_budget(max_tokens, "max_tokens")
        )

    @staticmethod
    def _validate_budget(value: int, name: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{name} must be a non-negative integer")
        return value

    def select(
        self,
        candidates: list[SourceChunk],
        max_tokens: int | None = None,
    ) -> tuple[list[SourceChunk], list[dict]]:
        """Select evidence using an explicit hard token budget when provided."""
        if max_tokens is not None or self.max_tokens is not None:
            return self.select_with_token_budget(candidates, max_tokens)
        return self._select_by_chars(candidates)

    def select_with_token_budget(
        self,
        candidates: list[SourceChunk],
        max_tokens: int | None = None,
    ) -> tuple[list[SourceChunk], list[dict]]:
        """Select evidence under a tokenizer-independent hard token proxy cap.

        The highest-scoring candidate is considered first.  Exact duplicates
        are dropped, and an oversized first candidate is kept only as a
        bounded excerpt so the selected context never exceeds the cap.
        """
        if max_tokens is None:
            max_tokens = self.max_tokens
        if max_tokens is None:
            raise ValueError("max_tokens is required for token-budget selection")
        max_tokens = self._validate_budget(max_tokens, "max_tokens")

        selected: list[SourceChunk] = []
        dropped: list[dict] = []
        seen_exact: set[str] = set()
        used = 0
        for chunk in sorted(candidates, key=lambda c: (-c.score, c.chunk_id)):
            cost = estimate_tokens(chunk.text)
            digest = self._digest(chunk.text)
            if digest in seen_exact:
                dropped.append(self._drop_record(chunk, "exact_duplicate", cost))
                continue

            remaining = max_tokens - used
            if cost <= remaining:
                seen_exact.add(digest)
                selected.append(chunk)
                used += cost
                continue

            if not selected and remaining > 0:
                excerpt = self._truncate_to_budget(chunk.text, remaining)
                allocated = estimate_tokens(excerpt)
                if excerpt:
                    seen_exact.add(digest)
                    selected.append(SourceChunk(**{**chunk.__dict__, "text": excerpt}))
                    used += allocated
                    dropped.append(
                        self._drop_record(
                            chunk,
                            "truncated_to_hard_context_token_cap",
                            cost,
                            allocated_tokens=allocated,
                        )
                    )
                    continue

            dropped.append(self._drop_record(chunk, "budget_exceeded", cost))
        return selected, dropped

    @staticmethod
    def _digest(text: str) -> str:
        return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()

    @staticmethod
    def _drop_record(
        chunk: SourceChunk,
        reason: str,
        estimated_tokens: int,
        allocated_tokens: int = 0,
    ) -> dict:
        return {
            "chunk_id": chunk.chunk_id,
            "reason": reason,
            "estimated_tokens": estimated_tokens,
            "allocated_tokens": allocated_tokens,
        }

    @staticmethod
    def _truncate_to_budget(text: str, max_tokens: int) -> str:
        clean = normalize_text(text)
        if max_tokens <= 0 or not clean:
            return ""

        excerpt = clean[: max_tokens * 3]
        while excerpt and estimate_tokens(excerpt) > max_tokens:
            excerpt = excerpt[:-1]
        return excerpt

    def _select_by_chars(self, candidates: list[SourceChunk]) -> tuple[list[SourceChunk], list[dict]]:
        """Keep the original character-budget behavior for existing callers."""
        selected: list[SourceChunk] = []
        dropped: list[dict] = []
        seen_exact: set[str] = set()
        used = 0
        for chunk in sorted(candidates, key=lambda c: (-c.score, c.chunk_id)):
            digest = self._digest(chunk.text)
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
