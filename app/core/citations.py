from __future__ import annotations

from collections.abc import Iterable

from app.core.types import SourceChunk


def validate_citations(
    citation_ids: Iterable[object] | None,
    available: Iterable[SourceChunk],
) -> tuple[list[str], list[str]]:
    """Keep only unique citation IDs that resolve to supplied evidence.

    The selected evidence packet is the authority for M0 locators. Empty,
    non-string, and unknown values are returned as invalid instead of being
    allowed to become source references by string coercion.
    """
    allowed = {
        chunk.chunk_id
        for chunk in available
        if isinstance(chunk, SourceChunk)
        and isinstance(chunk.chunk_id, str)
        and chunk.chunk_id
    }
    valid: list[str] = []
    invalid: list[str] = []
    seen: set[str] = set()

    if isinstance(citation_ids, (str, bytes)):
        citation_ids = (citation_ids,)

    for raw_citation in citation_ids or ():
        if not isinstance(raw_citation, str):
            marker = f"<{type(raw_citation).__name__}>"
            if marker not in seen:
                invalid.append(marker)
                seen.add(marker)
            continue
        cid = raw_citation.strip()
        if not cid:
            if "" not in seen:
                invalid.append("")
                seen.add("")
            continue
        if cid in seen:
            continue
        seen.add(cid)
        if cid in allowed:
            valid.append(cid)
        else:
            invalid.append(cid)
    return valid, invalid


def resolve_citations(
    citation_ids: Iterable[object] | None,
    available: Iterable[SourceChunk],
) -> tuple[list[str], list[str]]:
    """Resolve short evidence keys to canonical source/chunk locators.

    Evidence keys are application-owned labels such as ``E1`` and ``E2``.
    Exact canonical chunk IDs remain accepted for backward compatibility, but
    unknown, malformed, and truncated values still go through validation and
    are rejected.
    """
    evidence = list(available)
    evidence_keys = {
        f"E{index}": chunk.chunk_id
        for index, chunk in enumerate(evidence, start=1)
        if (
            isinstance(chunk, SourceChunk)
            and isinstance(chunk.chunk_id, str)
            and chunk.chunk_id
        )
    }
    if isinstance(citation_ids, (str, bytes)):
        values = (citation_ids,)
    else:
        values = citation_ids or ()

    resolved: list[object] = []
    for value in values:
        if isinstance(value, str):
            key = value.strip()
            resolved.append(evidence_keys.get(key, value))
        else:
            resolved.append(value)
    return validate_citations(resolved, evidence)
