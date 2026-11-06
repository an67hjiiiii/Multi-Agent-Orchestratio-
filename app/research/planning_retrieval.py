from __future__ import annotations
from app.core.types import SourceChunk
from app.retrieval.text import make_chunks, retrieve, terms

DEFAULT_PATTERNS = [
    ("planning_security.md", "Authentication, authorization, JWT, identity and access-control requests should remain separate atomic obligations when the user asks for distinct concerns."),
    ("planning_database.md", "Database review requests commonly decompose into schema/data model, query/access, transaction/consistency, and performance only when the user actually asks for them."),
    ("planning_api.md", "API and architecture requests commonly separate endpoint contract, error handling, integration boundary, dependency, and architecture decisions. Preserve user-stated dependencies."),
    ("planning_multi_domain.md", "Multi-domain software review requests should create one task per independent obligation, preserve required dependencies, avoid merging merely because terms are semantically similar, and avoid inventing tasks not requested."),
]

# These are distinctive cues from the current pattern text or stable source
# names. Shared prompt words such as "review" and "request" are not routing
# evidence for a pattern.
PLANNING_ANCHORS = {
    "planning_security.md": frozenset({"security", "authentication", "authorization", "jwt", "identity", "access-control", "control"}),
    "planning_database.md": frozenset({"database", "schema", "data", "model", "query", "transaction", "consistency", "performance"}),
    "planning_api.md": frozenset({"api", "architecture", "endpoint", "error", "handling", "integration", "dependency"}),
    "planning_multi_domain.md": frozenset({"multi-domain", "independent", "semantically", "merge", "invent"}),
}
PLANNING_SCORER_VERSION = "planning-lexical-intent-v2"

class PlanningRetriever:
    def __init__(self, min_score: float = 0.0):
        self.min_score = max(0.0, float(min_score))
        chunks: list[SourceChunk] = []
        for name, text in DEFAULT_PATTERNS:
            chunks.extend(make_chunks(name, text, max_chars=1000))
        self.chunks = chunks

    def search(
        self,
        query: str,
        top_k: int = 3,
        *,
        min_score: float | None = None,
    ) -> list[SourceChunk]:
        """Return ranked planning patterns with pattern-specific relevance."""

        query_terms = terms(query)
        eligible_names = {
            name for name, values in PLANNING_ANCHORS.items() if query_terms & values
        }
        intent_terms = query_terms & set().union(*(
            terms(" ".join(PLANNING_ANCHORS[name])) for name in eligible_names
        ))
        candidates = [
            SourceChunk(**{
                **chunk.__dict__, "text": f"{chunk.source_name}\n{chunk.text}"
            })
            for chunk in self.chunks
            if chunk.source_name in eligible_names
        ]
        score_floor = self.min_score if min_score is None else max(0.0, float(min_score))

        found = retrieve(
            " ".join(sorted(intent_terms)),
            candidates,
            top_k=top_k,
            min_score=score_floor,
        )
        originals = {chunk.chunk_id: chunk for chunk in self.chunks}
        return [
            SourceChunk(**{**originals[hit.chunk_id].__dict__, "score": hit.score})
            for hit in found
        ]
