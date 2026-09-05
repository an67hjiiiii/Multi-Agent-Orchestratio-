from __future__ import annotations
import json
import re
from app.core.citations import validate_citations
from app.core.types import RunMetrics, SourceChunk, TaskResult


def _extract_json(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            return {"status": "PARTIAL", "answer": text, "citations": [], "missing_information": []}
        return json.loads(m.group(0))


async def answer_vanilla(provider, query: str, evidence: list[SourceChunk], metrics: RunMetrics) -> TaskResult:
    if not evidence:
        return TaskResult(
            task_id="T1",
            domain="general",
            status="NO_EVIDENCE",
            answer="Không tìm thấy bằng chứng phù hợp trong nguồn đã nạp để trả lời yêu cầu này.",
            evidence_ids=[],
            citations=[],
            missing_information=["relevant evidence"],
        )

    evidence_text = "\n\n".join(f"[{c.chunk_id}] {c.text}" for c in evidence)
    system = (
        "VANILLA_RAG_ANSWERER. Use only supplied evidence. Return JSON only. "
        "Every factual claim that comes from the corpus must be grounded by one or more exact chunk IDs. "
        "If evidence is insufficient, return PARTIAL or NO_EVIDENCE and do not invent citations."
    )
    user = (
        f"USER REQUEST:\n{query}\n\nEVIDENCE:\n{evidence_text}\n\n"
        'Schema: {"status":"COMPLETE|PARTIAL|NO_EVIDENCE","answer":"...",'
        '"citations":["chunk_id"],"missing_information":[]}'
    )
    result = await provider.generate(system=system, user=user)
    metrics.add_usage(result.usage)
    obj = _extract_json(result.text)
    raw_citations = [str(x) for x in obj.get("citations") or []]
    valid, invalid = validate_citations(raw_citations, evidence)
    metrics.add_citations(valid, invalid)

    status = str(obj.get("status") or "PARTIAL").upper()
    answer = str(obj.get("answer") or "").strip()
    missing = [str(x) for x in obj.get("missing_information") or []]
    if invalid:
        status = "PARTIAL"
        missing.append("invalid citation locator(s) removed")
    if status == "COMPLETE" and not valid:
        status = "PARTIAL"
        missing.append("answer has no valid citation")

    if valid:
        answer = answer.rstrip() + "\n\nNguồn: " + ", ".join(f"[{cid}]" for cid in valid)

    return TaskResult(
        task_id="T1",
        domain="general",
        status=status,
        answer=answer,
        evidence_ids=[c.chunk_id for c in evidence],
        citations=valid,
        invalid_citations=invalid,
        missing_information=missing,
    )
