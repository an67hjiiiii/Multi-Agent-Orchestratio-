"""Validate one worker response against its selected evidence packet."""

from __future__ import annotations

import json
import re

from app.core.citations import resolve_citations
from app.core.types import RunMetrics, SourceChunk, Task
from app.research.contracts import WorkerResult


def _extract_json(text: str) -> dict:
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"\{.*\}", text, re.S)
        return (
            json.loads(match.group(0))
            if match
            else {
                "status": "PARTIAL",
                "answer": text,
                "citations": [],
                "missing_information": [],
            }
        )


def verify_worker_response(
    response_text: str,
    task: Task,
    evidence: list[SourceChunk],
    metrics: RunMetrics,
) -> WorkerResult:
    """Return the established worker result after citation and status checks."""

    payload = _extract_json(response_text)
    valid, invalid = resolve_citations(payload.get("citations"), evidence)
    metrics.add_citations(valid, invalid)
    status = str(payload.get("status") or "PARTIAL").upper()
    missing = [str(item) for item in payload.get("missing_information") or []]
    status_reason = ""
    if invalid:
        status = "PARTIAL"
        missing.append("invalid citation locator(s) removed")
        status_reason = "INVALID_CITATION_LOCATOR"
    if status == "COMPLETE" and not valid:
        status = "PARTIAL"
        missing.append("worker answer has no valid citation")
        status_reason = "NO_VALID_CITATION"
    if status == "PARTIAL" and not missing:
        status_reason = "WORKER_PARTIAL_WITHOUT_REASON"
    return WorkerResult(
        task_id=task.task_id,
        domain=task.domain,
        status=status,
        answer=str(payload.get("answer") or ""),
        evidence_ids=[chunk.chunk_id for chunk in evidence],
        citations=valid,
        invalid_citations=invalid,
        missing_information=missing,
        status_reason=status_reason,
    )
