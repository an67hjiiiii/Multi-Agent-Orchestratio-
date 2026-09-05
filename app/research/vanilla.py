from __future__ import annotations
import json
from app.core.citations import validate_citations
from app.core.types import RunMetrics, SourceChunk, TaskResult


_ANSWER_STATUSES = frozenset({"COMPLETE", "PARTIAL", "NO_EVIDENCE"})
_NO_EVIDENCE_ANSWER = "Không tìm thấy bằng chứng phù hợp trong nguồn đã nạp để trả lời yêu cầu này."


def _partial_payload(text: str) -> dict:
    return {
        "status": "PARTIAL",
        "answer": text,
        "citations": [],
        "missing_information": [],
    }


def _extract_json(text: str) -> dict:
    text = str(text or "").strip()
    try:
        value = json.loads(text)
    except (TypeError, ValueError):
        # Some local models wrap JSON in a short preamble or a markdown fence.
        # Decode the first complete object without using a greedy brace regex;
        # braces can legitimately occur inside an answer string.
        decoder = json.JSONDecoder()
        for start, character in enumerate(text):
            if character != "{":
                continue
            try:
                value, _ = decoder.raw_decode(text[start:])
            except ValueError:
                continue
            if isinstance(value, dict):
                return value
        return _partial_payload(text)

    return value if isinstance(value, dict) else _partial_payload(text)


def _string_values(value: object) -> tuple[list[str], bool]:
    """Return normalized values and whether the JSON field had list shape."""
    if value is None:
        return [], True
    if not isinstance(value, list):
        values = [value]
        list_shape = False
    else:
        values = value
        list_shape = all(isinstance(item, str) for item in value)
    normalized: list[str] = []
    for item in values:
        item_text = str(item).strip()
        if item_text:
            normalized.append(item_text)
    return normalized, list_shape


def _append_missing(missing: list[str], message: str) -> None:
    if message not in missing:
        missing.append(message)


async def answer_vanilla(provider, query: str, evidence: list[SourceChunk], metrics: RunMetrics) -> TaskResult:
    if not evidence:
        return TaskResult(
            task_id="T1",
            domain="general",
            status="NO_EVIDENCE",
            answer=_NO_EVIDENCE_ANSWER,
            evidence_ids=[],
            citations=[],
            missing_information=["relevant evidence"],
        )

    evidence_text = "\n\n".join(f"[{c.chunk_id}] {c.text}" for c in evidence)
    system = (
        "VANILLA_RAG_ANSWERER. Use only supplied evidence. Return JSON only with the schema "
        '{"status":"COMPLETE|PARTIAL|NO_EVIDENCE","answer":"...",'
        '"citations":["exact chunk_id"],"missing_information":["..."]}. '
        "Every factual claim from the corpus must be grounded by one or more exact supplied chunk IDs. "
        "Use COMPLETE only for a fully supported answer, PARTIAL when information or validation is incomplete, "
        "and NO_EVIDENCE when the supplied evidence cannot answer the request. Never invent citations."
    )
    user = (
        f"USER REQUEST:\n{query}\n\nEVIDENCE:\n{evidence_text}\n\n"
        'Schema: {"status":"COMPLETE|PARTIAL|NO_EVIDENCE","answer":"...",'
        '"citations":["chunk_id"],"missing_information":[]}'
    )
    result = await provider.generate(system=system, user=user)
    metrics.add_usage(result.usage)
    obj = _extract_json(result.text)
    raw_citations, citations_shape_ok = _string_values(obj.get("citations"))
    valid, invalid = validate_citations(raw_citations, evidence)
    metrics.add_citations(valid, invalid)

    raw_status = obj.get("status")
    status = raw_status.strip().upper() if isinstance(raw_status, str) else "PARTIAL"
    schema_issues: list[str] = []
    if status not in _ANSWER_STATUSES:
        status = "PARTIAL"
        _append_missing(schema_issues, "invalid terminal status")

    raw_answer = obj.get("answer")
    if raw_answer is None:
        answer = ""
    elif isinstance(raw_answer, str):
        answer = raw_answer.strip()
    else:
        answer = str(raw_answer).strip()
        _append_missing(schema_issues, "answer must be a string")

    missing, missing_shape_ok = _string_values(obj.get("missing_information"))
    if not citations_shape_ok:
        _append_missing(schema_issues, "citations must be an array")
    if not missing_shape_ok:
        _append_missing(schema_issues, "missing_information must be an array")

    for issue in schema_issues:
        _append_missing(missing, issue)
    if invalid:
        status = "PARTIAL"
        _append_missing(missing, "invalid citation locator(s) removed")
    if status == "COMPLETE" and not answer:
        status = "PARTIAL"
        _append_missing(missing, "answer text is empty")
    if status == "COMPLETE" and not valid:
        status = "PARTIAL"
        _append_missing(missing, "answer has no valid citation")
    if status == "COMPLETE" and missing:
        status = "PARTIAL"
    if status == "NO_EVIDENCE" and not missing:
        _append_missing(missing, "relevant evidence")

    if valid and answer:
        answer = answer.rstrip() + "\n\nNguồn: " + ", ".join(f"[{cid}]" for cid in valid)
    if status == "NO_EVIDENCE" and not answer:
        answer = _NO_EVIDENCE_ANSWER

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
