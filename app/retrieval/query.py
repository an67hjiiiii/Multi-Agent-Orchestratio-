"""Query-time retrieval policy over canonical source chunks."""

from __future__ import annotations

from dataclasses import replace

from app.core.types import SourceChunk
from app.retrieval.embeddings import TextEmbedder
from app.retrieval.text import domain_compatibility, retrieve
from app.storage.vector_store import VectorBackendUnavailable, VectorStore


def retrieve_chunks(
    query: str,
    chunks: list[SourceChunk],
    *,
    retrieval_mode: str,
    vector_store: VectorStore | None,
    embedder: TextEmbedder | None,
    top_k: int = 6,
    min_score: float = 0.0,
    domain: str | None = None,
    task_domain: str | None = None,
    owner_id: str | None = None,
    availability_error: str | None = None,
) -> list[SourceChunk]:
    """Run the existing lexical, vector, or hybrid query policy.

    Source lifecycle and index writes stay with Knowledge; this function only
    ranks the supplied canonical chunks and shapes query results.
    """

    lexical = retrieve(
        query,
        chunks,
        top_k=top_k,
        min_score=min_score,
        domain=domain,
        task_domain=task_domain,
    )
    if retrieval_mode == "LEXICAL":
        return lexical

    if vector_store is None or embedder is None:
        detail = availability_error or "vector backend is unavailable"
        raise VectorBackendUnavailable(detail)

    query_vector = embedder.embed(query)
    limit = max(top_k, top_k * 2)
    matches = (
        vector_store.search(query_vector, limit=limit)
        if owner_id is None
        else vector_store.search(query_vector, limit=limit, owner_id=owner_id)
    )
    by_id = {chunk.chunk_id: chunk for chunk in chunks}
    vector_scores: dict[str, float] = {}
    for match in matches:
        chunk = by_id.get(match.id)
        if chunk is None or match.score <= 0:
            continue
        vector_scores[chunk.chunk_id] = float(match.score)

    lexical_scores = {chunk.chunk_id: float(chunk.score) for chunk in lexical}
    if retrieval_mode == "VECTOR":
        candidate_ids = list(vector_scores)

        def score_for(chunk_id: str) -> float:
            return vector_scores[chunk_id]
    else:
        candidate_ids = list(dict.fromkeys([*lexical_scores, *vector_scores]))

        def score_for(chunk_id: str) -> float:
            lexical_score = lexical_scores.get(chunk_id, 0.0)
            vector_score = vector_scores.get(chunk_id, 0.0)
            return round(0.65 * lexical_score + 0.35 * vector_score, 8)

    requested_domain = task_domain if task_domain is not None else domain
    candidates: list[SourceChunk] = []
    for chunk_id in candidate_ids:
        chunk = by_id[chunk_id]
        score = score_for(chunk_id)
        if score <= 0 or score < min_score:
            continue
        candidates.append(replace(chunk, score=score))
    candidates.sort(
        key=lambda item: (
            -domain_compatibility(item, requested_domain),
            -item.score,
            item.chunk_id,
        )
    )
    return candidates[:top_k]


__all__ = ["retrieve_chunks"]
