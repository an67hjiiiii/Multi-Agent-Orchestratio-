from __future__ import annotations
import hashlib
from app.core.types import SourceChunk
from app.retrieval.text import (
    estimate_tokens,
    normalize_text,
    terms as lexical_terms,
    truncate_to_token_budget,
)


class OverlapTracker:
    """Record cross-task evidence reuse without globally removing evidence."""

    def __init__(self) -> None:
        self._selected_by_id: dict[str, list[str]] = {}

    def observe(self, task_id: str, selected: list[SourceChunk]) -> dict[str, object]:
        shared: dict[str, list[str]] = {}
        for chunk in selected:
            previous = self._selected_by_id.setdefault(chunk.chunk_id, [])
            if previous:
                shared[chunk.chunk_id] = list(previous)
            previous.append(task_id)
        return {
            "shared_evidence_ids": sorted(shared),
            "reused_from_task_ids": shared,
            "reuse_count": len(shared),
        }

    def summary(self) -> dict[str, object]:
        shared = {
            chunk_id: task_ids
            for chunk_id, task_ids in self._selected_by_id.items()
            if len(task_ids) > 1
        }
        return {"shared_evidence_ids": sorted(shared), "reuse_by_evidence_id": shared}

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
                excerpt = truncate_to_token_budget(chunk.text, remaining)
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

    def select_for_task(self, candidates: list[SourceChunk], *, task_terms: set[str], max_tokens: int) -> tuple[list[SourceChunk], list[dict], list[dict]]:
        """M1 O-lite: task relevance, exact/span de-duplication, and hard cap."""
        retained: list[SourceChunk] = []
        dropped: list[dict] = []
        for chunk in sorted(candidates, key=lambda item: (-item.score, item.chunk_id)):
            chunk_terms = lexical_terms(chunk.text)
            if chunk.score <= 0 or (task_terms and not task_terms.intersection(chunk_terms)):
                dropped.append(self._drop_record(chunk, "low_relevance", estimate_tokens(chunk.text)))
            else:
                retained.append(chunk)
        without_overlap: list[SourceChunk] = []
        for chunk in retained:
            clean = normalize_text(chunk.text)
            if any(existing.source_id == chunk.source_id and (clean in normalize_text(existing.text) or normalize_text(existing.text) in clean) for existing in without_overlap):
                dropped.append(self._drop_record(chunk, "overlapping_span", estimate_tokens(chunk.text)))
            else:
                without_overlap.append(chunk)
        selected, cap_drops = self.select_with_token_budget(without_overlap, max_tokens)
        dropped.extend(cap_drops)
        by_id = {item.chunk_id: item for item in candidates}
        for record in dropped:
            chunk = by_id.get(record["chunk_id"])
            if chunk is not None:
                record.update({"source_id": chunk.source_id, "locator": chunk.index})
        # Cross-task sharing is reported by OverlapTracker after this local
        # selection.  Do not claim sharing before another task has reused it.
        selected_log = [{"chunk_id": item.chunk_id, "source_id": item.source_id, "locator": item.index, "score": item.score, "reason": "retained"} for item in selected]
        return selected, dropped, selected_log

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
        """Keep the legacy private hook on the shared token implementation."""

        return truncate_to_token_budget(text, max_tokens)

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
