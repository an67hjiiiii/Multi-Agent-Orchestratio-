from __future__ import annotations
import json
import re
from app.core.citations import resolve_citations
from app.core.types import Task, TaskResult, SourceChunk, RunMetrics
from app.research.registry import profile


def _extract_json(text: str) -> dict:
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.S)
        return json.loads(m.group(0)) if m else {"status":"PARTIAL","answer":text,"citations":[],"missing_information":[]}

async def execute_task(provider, task: Task, evidence: list[SourceChunk], metrics: RunMetrics) -> TaskResult:
    if not evidence:
        return TaskResult(
            task_id=task.task_id,
            domain=task.domain,
            status="NO_EVIDENCE",
            answer="Chưa tìm thấy evidence phù hợp cho task này.",
            evidence_ids=[],
            citations=[],
            missing_information=["relevant evidence"],
        )
    p = profile(task.domain)
    # The application owns the stable E1/E2 mapping, as it does for Vanilla
    # RAG. Short keys prevent the local model from truncating a canonical ID.
    evidence_text = "\n\n".join(
        f"[E{index}] [{chunk.chunk_id}] {chunk.text}"
        for index, chunk in enumerate(evidence, start=1)
    )
    system = (
        f"WORKER. Role={p['name']}. Scope={p['scope']}. Exclusions={p['exclusions']}. "
        "Use only supplied evidence; if insufficient, return NO_EVIDENCE or PARTIAL. "
        "Return JSON only and cite only exact supplied evidence keys E1, E2, etc."
    )
    user = (
        f"[DOMAIN]{task.domain}[/DOMAIN]\n[TASK]{task.goal}[/TASK]\n[EVIDENCE]{evidence_text}[/EVIDENCE]\n"
        'Schema: {"status":"COMPLETE|PARTIAL|NO_EVIDENCE","answer":"...",'
        '"citations":["E1"],"missing_information":[]}'
    )
    result = await provider.generate(system=system, user=user)
    metrics.add_usage(result.usage)
    obj = _extract_json(result.text)
    raw_citations = obj.get("citations")
    valid, invalid = resolve_citations(raw_citations, evidence)
    metrics.add_citations(valid, invalid)
    status = str(obj.get("status") or "PARTIAL").upper()
    missing = [str(x) for x in obj.get("missing_information") or []]
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
    return TaskResult(
        task_id=task.task_id,
        domain=task.domain,
        status=status,
        answer=str(obj.get("answer") or ""),
        evidence_ids=[c.chunk_id for c in evidence],
        citations=valid,
        invalid_citations=invalid,
        missing_information=missing,
        status_reason=status_reason,
    )
