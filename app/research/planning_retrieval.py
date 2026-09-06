from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from importlib import import_module
import math
from typing import Any

from app.retrieval.text import estimate_tokens, terms


DEFAULT_TOP_K = 3
DEFAULT_MAX_CONTEXT_TOKENS = 1_200
DEFAULT_MIN_SCORE = 0.18


@dataclass(frozen=True)
class PlanningKnowledgeItem:
    """One versioned item from the separate Planning KB."""

    id: str
    domain: str
    title: str
    content: str
    provenance: str


@dataclass(frozen=True)
class _PlanningHit:
    """Small compatibility view for the pre-Sprint-3 pipeline wiring."""

    chunk_id: str
    text: str
    score: float = 0.0


@dataclass(frozen=True)
class PlanningRetrievalResult:
    """Bounded planning context and the IDs selected from the Planning KB."""

    request: str
    item_ids: list[str]
    scores: list[float] | None
    context: str

    def __iter__(self):
        """Keep old ``search`` callers readable during the wiring transition."""

        return iter(getattr(self, "_compatibility_hits", ()))

    def __len__(self) -> int:
        return len(self.item_ids)

    def __getitem__(self, index: int) -> _PlanningHit:
        return tuple(getattr(self, "_compatibility_hits", ()))[index]


@dataclass(frozen=True)
class _ScoredItem:
    item: PlanningKnowledgeItem
    score: float


@dataclass(frozen=True)
class _BoundedItem:
    item: PlanningKnowledgeItem
    score: float
    text: str


class PlanningRetriever:
    """Retrieve bounded, lexical planning guidance from a separate KB.

    The retriever deliberately does not reuse answer-domain ``SourceChunk``
    data.  A caller may inject an iterable of planning items or a KB object
    exposing ``items``/``all_items``.  With no injection, the optional
    ``app.planning.kb`` module is loaded; an unavailable KB produces an empty
    result rather than invented planning evidence.
    """

    def __init__(
        self,
        kb: Any | None = None,
        *,
        items: Iterable[PlanningKnowledgeItem] | None = None,
        top_k: int = DEFAULT_TOP_K,
        max_context_tokens: int = DEFAULT_MAX_CONTEXT_TOKENS,
        min_score: float = DEFAULT_MIN_SCORE,
        expose_scores: bool = False,
    ) -> None:
        if kb is not None and items is not None:
            raise ValueError("pass either kb or items, not both")

        self.top_k = _positive_int("top_k", top_k)
        self.max_context_tokens = _positive_int(
            "max_context_tokens", max_context_tokens
        )
        self.min_score = _non_negative_finite("min_score", min_score)
        if not isinstance(expose_scores, bool):
            raise TypeError("expose_scores must be a boolean")
        self.expose_scores = expose_scores

        raw_items = (
            items
            if items is not None
            else _items_from_kb(kb) if kb is not None else _load_default_items()
        )
        self.items = _normalise_items(raw_items)

    def retrieve(
        self,
        request: str,
        top_k: int | None = None,
        *,
        include_scores: bool | None = None,
        expose_scores: bool | None = None,
    ) -> PlanningRetrievalResult:
        """Return the relevant Planning KB items and bounded context.

        Relevance is gated before the top-k cap.  Therefore an unrelated
        request returns no items instead of receiving an arbitrary top item.
        ``scores`` stays ``None`` unless score exposure is explicitly enabled.
        """

        clean_request = _request_text(request)
        limit = self.top_k if top_k is None else _positive_int("top_k", top_k)
        score_exposure = self._score_exposure(include_scores, expose_scores)

        scored = self._rank(clean_request)
        selected = self._bounded_selection(scored[:limit])
        result = PlanningRetrievalResult(
            request=clean_request,
            item_ids=[entry.item.id for entry in selected],
            scores=(
                [entry.score for entry in selected] if score_exposure else None
            ),
            context="\n\n".join(entry.text for entry in selected),
        )
        compatibility_hits = tuple(
            _PlanningHit(
                chunk_id=entry.item.id,
                text=entry.text,
                score=entry.score,
            )
            for entry in selected
        )
        object.__setattr__(result, "_compatibility_hits", compatibility_hits)
        return result

    def search(
        self,
        request: str,
        top_k: int | None = None,
        *,
        include_scores: bool | None = None,
        expose_scores: bool | None = None,
    ) -> PlanningRetrievalResult:
        """Alias for ``retrieve`` used by the existing pipeline boundary."""

        return self.retrieve(
            request,
            top_k=top_k,
            include_scores=include_scores,
            expose_scores=expose_scores,
        )

    def _rank(self, request: str) -> list[_ScoredItem]:
        query_terms = terms(request)
        if not query_terms:
            return []

        scored: list[_ScoredItem] = []
        for item in self.items:
            item_terms = terms(f"{item.domain} {item.title} {item.content}")
            overlap = len(query_terms & item_terms)
            if overlap == 0:
                continue
            coverage = overlap / len(query_terms)
            density = overlap / max(1, len(item_terms))
            score = round(0.8 * coverage + 0.2 * density, 8)
            if score >= self.min_score:
                scored.append(_ScoredItem(item=item, score=score))

        scored.sort(key=lambda entry: (-entry.score, entry.item.id))
        return scored

    def _bounded_selection(self, ranked: list[_ScoredItem]) -> list[_BoundedItem]:
        selected: list[_BoundedItem] = []
        used_tokens = 0
        for entry in ranked:
            rendered = self._render(entry.item)
            item_tokens = estimate_tokens(rendered)
            if used_tokens + item_tokens <= self.max_context_tokens:
                selected.append(
                    _BoundedItem(item=entry.item, score=entry.score, text=rendered)
                )
                used_tokens += item_tokens
                continue

            if not selected:
                bounded = _truncate_to_tokens(rendered, self.max_context_tokens)
                selected.append(
                    _BoundedItem(
                        item=entry.item,
                        score=entry.score,
                        text=bounded,
                    )
                )
            break
        return selected

    @staticmethod
    def _render(item: PlanningKnowledgeItem) -> str:
        return (
            f"[{item.id}] domain={item.domain}; title={item.title}\n"
            f"{item.content}\n"
            f"provenance={item.provenance}"
        )

    def _score_exposure(
        self,
        include_scores: bool | None,
        expose_scores: bool | None,
    ) -> bool:
        if include_scores is not None and not isinstance(include_scores, bool):
            raise TypeError("include_scores must be a boolean")
        if expose_scores is not None and not isinstance(expose_scores, bool):
            raise TypeError("expose_scores must be a boolean")
        if include_scores is not None and expose_scores is not None:
            raise ValueError("pass either include_scores or expose_scores, not both")
        if include_scores is not None:
            return include_scores
        if expose_scores is not None:
            return expose_scores
        return self.expose_scores


def _load_default_items() -> tuple[PlanningKnowledgeItem, ...]:
    """Load the separate KB when it has been integrated into the checkout."""

    try:
        module = import_module("app.planning.kb")
    except ModuleNotFoundError as exc:
        if exc.name in {"app.planning", "app.planning.kb"}:
            return ()
        raise

    for loader_name in (
        "load_planning_items",
        "get_planning_items",
        "load_planning_kb",
        "load_items",
    ):
        loader = getattr(module, loader_name, None)
        if callable(loader):
            return tuple(_normalise_items(_items_from_kb(loader())))

    for constant_name in ("PLANNING_ITEMS", "DEFAULT_ITEMS", "ITEMS"):
        if hasattr(module, constant_name):
            return tuple(_normalise_items(getattr(module, constant_name)))

    knowledge_base = getattr(module, "PlanningKnowledgeBase", None)
    if knowledge_base is not None:
        instance = knowledge_base() if callable(knowledge_base) else knowledge_base
        return tuple(_normalise_items(_items_from_kb(instance)))

    raise RuntimeError(
        "app.planning.kb must expose a planning-item loader or item collection"
    )


def _items_from_kb(kb: Any) -> Iterable[Any]:
    if isinstance(kb, Mapping):
        return kb.values()
    if callable(kb):
        return kb()

    for attribute_name in ("items", "all_items"):
        attribute = getattr(kb, attribute_name, None)
        if attribute is not None:
            return attribute() if callable(attribute) else attribute
    return kb


def _normalise_items(raw_items: Iterable[Any]) -> tuple[PlanningKnowledgeItem, ...]:
    if raw_items is None:
        return ()
    if isinstance(raw_items, (str, bytes)):
        raise TypeError("planning items must be an iterable of item records")

    result: list[PlanningKnowledgeItem] = []
    seen_ids: set[str] = set()
    for raw_item in raw_items:
        item = _coerce_item(raw_item)
        if item.id in seen_ids:
            continue
        seen_ids.add(item.id)
        result.append(item)
    return tuple(result)


def _coerce_item(raw_item: Any) -> PlanningKnowledgeItem:
    values: dict[str, Any]
    if isinstance(raw_item, Mapping):
        values = dict(raw_item)
    else:
        values = {
            field_name: getattr(raw_item, field_name, None)
            for field_name in ("id", "domain", "title", "content", "provenance")
        }

    clean: dict[str, str] = {}
    for field_name in ("id", "domain", "title", "content", "provenance"):
        value = values.get(field_name)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"planning item field {field_name!r} must be a non-empty string"
            )
        clean[field_name] = value.strip()
    return PlanningKnowledgeItem(**clean)


def _request_text(request: str) -> str:
    if not isinstance(request, str):
        raise TypeError("request must be a string")
    clean = request.strip()
    if not clean:
        raise ValueError("request must not be empty")
    return clean


def _positive_int(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _non_negative_finite(name: str, value: float) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        raise ValueError(f"{name} must be a finite non-negative number")
    return float(value)


def _truncate_to_tokens(text: str, max_tokens: int) -> str:
    char_cap = max(1, max_tokens * 3 - 2)
    return text[:char_cap]
