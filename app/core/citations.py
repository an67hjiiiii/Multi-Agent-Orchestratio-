from __future__ import annotations
from app.core.types import SourceChunk


def validate_citations(citation_ids: list[str], available: list[SourceChunk]) -> tuple[list[str], list[str]]:
    allowed = {c.chunk_id for c in available}
    valid: list[str] = []
    invalid: list[str] = []
    seen: set[str] = set()
    for cid in citation_ids:
        cid = str(cid).strip()
        if not cid or cid in seen:
            continue
        seen.add(cid)
        if cid in allowed:
            valid.append(cid)
        else:
            invalid.append(cid)
    return valid, invalid
