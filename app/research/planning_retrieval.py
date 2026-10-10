from __future__ import annotations
from app.core.types import SourceChunk
from app.retrieval.text import make_chunks, retrieve

DEFAULT_PATTERNS = [
    ("planning_security.md", "Authentication, authorization, JWT, identity and access-control requests should remain separate atomic obligations when the user asks for distinct concerns."),
    ("planning_database.md", "Database review requests commonly decompose into schema/data model, query/access, transaction/consistency, and performance only when the user actually asks for them."),
    ("planning_api.md", "API and architecture requests commonly separate endpoint contract, error handling, integration boundary, dependency, and architecture decisions. Preserve user-stated dependencies."),
    ("planning_multi_domain.md", "Multi-domain software review requests should create one task per independent obligation, preserve required dependencies, avoid merging merely because terms are semantically similar, and avoid inventing tasks not requested."),
]

class PlanningRetriever:
    def __init__(self):
        chunks: list[SourceChunk] = []
        for name, text in DEFAULT_PATTERNS:
            chunks.extend(make_chunks(name, text, max_chars=1000))
        self.chunks = chunks

    def search(self, query: str, top_k: int = 3) -> list[SourceChunk]:
        found = retrieve(query, self.chunks, top_k=top_k)
        return found or self.chunks[:top_k]
