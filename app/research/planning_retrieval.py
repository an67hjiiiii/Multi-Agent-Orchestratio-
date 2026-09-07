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

# Traceable, deterministic relevance contract for the Planning KB.  This is
# intentionally separate from answer-domain retrieval scoring.
PLANNING_RETRIEVAL_SCORING_VERSION = "idf-content-anchor-v1"

# Question scaffolding is not planning evidence.  Removing only these terms
# prevents a word such as "when" or "review" from making an unrelated KB item
# look relevant while retaining domain/obligation terms such as "request".
_PLANNING_QUERY_STOPWORDS = frozenset(
    {
        "when",
        "what",
        "which",
        "how",
        "why",
        "review",
        "check",
        "identify",
        "determine",
        "suggest",
        "required",
    }
)

# Content anchors carry more relevance than a match found only in a title or
# domain label.  This keeps a transaction request anchored to the database
# guidance instead of an API item whose title happens to contain "boundaries".
_CONTENT_ANCHOR_WEIGHT = 1.0
_TITLE_ANCHOR_WEIGHT = 0.25
_DOMAIN_ANCHOR_WEIGHT = 0.15
_SECONDARY_ANCHOR_WEIGHT = 0.25
_PLANNING_QUERY_CONNECTORS = frozenset(
    {"and", "or", "then", "first", "second", "independently", "also"}
)


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
        query_groups = _planning_query_term_groups(request)
        query_terms = {term for group in query_groups for term in group}
        if not query_terms:
            return []

        secondary_anchors = {
            term: group[index - 1]
            for group in query_groups
            for index, term in enumerate(group)
            if index > 0
        }

        indexed_items = [
            (
                item,
                terms(item.domain),
                terms(item.title),
                terms(item.content),
            )
            for item in self.items
        ]
        document_frequency = {
            query_term: sum(
                query_term in (domain_terms | title_terms | content_terms)
                for _, domain_terms, title_terms, content_terms in indexed_items
            )
            for query_term in query_terms
        }
        # Query terms absent from the Planning KB cannot discriminate among
        # planning items.  Excluding them from the denominator keeps a
        # multi-domain request from losing its known database/API/security
        # anchors merely because it also mentions an unrepresented detail.
        query_terms = {
            query_term for query_term in query_terms
            if document_frequency[query_term] > 0
        }
        if not query_terms:
            return []
        item_count = len(indexed_items)
        inverse_document_frequency = {
            query_term: math.log(
                (item_count + 1) / (document_frequency[query_term] + 1)
            )
            + 1.0
            for query_term in query_terms
        }
        query_weight = sum(inverse_document_frequency.values())

        scored: list[_ScoredItem] = []
        for item, domain_terms, title_terms, content_terms in indexed_items:
            item_terms = domain_terms | title_terms | content_terms
            overlap = query_terms & item_terms
            if not overlap:
                continue

            weighted_overlap = 0.0
            for query_term in overlap:
                if query_term in content_terms:
                    anchor_weight = _CONTENT_ANCHOR_WEIGHT
                elif query_term in title_terms:
                    anchor_weight = _TITLE_ANCHOR_WEIGHT
                else:
                    anchor_weight = _DOMAIN_ANCHOR_WEIGHT
                predecessor = secondary_anchors.get(query_term)
                if (
                    len(query_terms) <= 2
                    and predecessor is not None
                    and predecessor not in item_terms
                ):
                    anchor_weight *= _SECONDARY_ANCHOR_WEIGHT
                weighted_overlap += (
                    inverse_document_frequency[query_term] * anchor_weight
                )

            weighted_item_mass = sum(
                inverse_document_frequency.get(item_term, 1.0)
                for item_term in item_terms
            )
            coverage = weighted_overlap / max(1e-12, query_weight)
            density = weighted_overlap / max(1.0, weighted_item_mass)
            score = round(0.9 * coverage + 0.1 * density, 8)
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


def _planning_query_term_groups(request: str) -> list[list[str]]:
    """Keep adjacent obligation terms while separating independent clauses."""

    groups: list[list[str]] = []
    current: list[str] = []
    for raw_token in request.split():
        marker = raw_token.casefold().strip(".,;:!?()[]{}")
        if marker in _PLANNING_QUERY_CONNECTORS:
            if current:
                groups.append(current)
                current = []
            continue
        token_terms = terms(raw_token) - _PLANNING_QUERY_STOPWORDS
        if token_terms:
            # A token normally yields one normalized term; sorting keeps
            # hyphenated/multi-part tokens deterministic if that changes.
            current.extend(sorted(token_terms))
    if current:
        groups.append(current)
    return groups


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
