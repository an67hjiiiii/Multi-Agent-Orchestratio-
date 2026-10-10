from __future__ import annotations
import json

from app.core.citations import resolve_citation_ids
from app.core.types import TaskResult, RunMetrics
from app.research.contracts import WorkerResult


def _json_object(text: str) -> dict:
    try:
        value = json.loads(text)
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _fallback_answer(query: str, results: list[TaskResult]) -> str:
    """Build a concise grounded answer when model JSON is empty or too thin."""

    usable = [result for result in results if result.answer.strip()]
    if not usable or all(result.status == "NO_EVIDENCE" for result in results):
        missing = sorted(
            {
                item
                for result in results
                for item in result.missing_information
                if item.strip()
            }
        )
        suffix = f" Thiếu: {', '.join(missing)}." if missing else ""
        return f"Chưa có đủ bằng chứng để trả lời câu hỏi này.{suffix}"

    first = usable[0].answer.strip()
    lines = [f"Kết luận: {first}"]
    for result in usable[1:]:
        label = "Bổ sung" if result.status == "COMPLETE" else "Giới hạn"
        lines.append(f"{label}: {result.answer.strip()}")

    missing = sorted(
        {
            item
            for result in results
            if result.status in {"PARTIAL", "NO_EVIDENCE"}
            for item in result.missing_information
            if item.strip()
        }
    )
    if missing:
        lines.append(f"Chưa xác định được: {', '.join(missing)}.")
    return "\n\n".join(lines)


def _answer_is_usable(answer: object) -> bool:
    if not isinstance(answer, str):
        return False
    clean = " ".join(answer.split())
    return len(clean) >= 24 and clean.casefold() not in {"ok", "yes", "no"}

async def synthesize_completed_results(
    provider, query: str, results: list[WorkerResult], metrics: RunMetrics
) -> str:
    """Consolidate completed worker results through the existing citation policy."""
    compact = []
    available_ids: list[str] = []
    worker_citations: list[str] = []
    for r in results:
        available_ids.extend(r.evidence_ids)
        worker_citations.extend(r.citations)
        compact.append(
            f"TASK {r.task_id} [{r.domain}] status={r.status}\n"
            f"answer={r.answer}\n"
            f"status_reason={r.status_reason}\n"
            f"worker_citations={','.join(r.citations)}\n"
            f"available_evidence={','.join(r.evidence_ids)}\n"
            f"missing={','.join(r.missing_information)}"
        )
    available_ids = list(dict.fromkeys(available_ids))
    system = (
        "SYNTHESIZER. PROMPT VERSION: synthesis-v2. Answer the user's question first, "
        "then combine the supplied task findings into a concise natural response. "
        "Use only supplied answers and evidence; never invent facts or repeat internal trace text. "
        "State uncertainty and missing information clearly for PARTIAL or NO_EVIDENCE tasks. "
        "Return JSON only: {\"answer\":\"...\",\"citations\":[\"E1\"]}. "
        "Citations may contain only supplied E-keys."
    )
    evidence_keys = "\n".join(f"E{index}={item}" for index, item in enumerate(available_ids, start=1))
    user = f"USER REQUEST:\n{query}\n\nAVAILABLE EVIDENCE KEYS:\n{evidence_keys}\n\nTASK RESULTS:\n" + "\n\n".join(compact)
    result = await provider.generate(system=system, user=user)
    metrics.add_usage(result.usage)
    payload = _json_object(result.text)
    answer = payload.get("answer")
    if not _answer_is_usable(answer):
        answer = _fallback_answer(query, results)
    synthesis_valid, synthesis_invalid = resolve_citation_ids(payload.get("citations"), available_ids)
    worker_valid, _ = resolve_citation_ids(worker_citations, available_ids)
    metrics.add_citations(synthesis_valid, synthesis_invalid)
    canonical = list(dict.fromkeys([*worker_valid, *synthesis_valid]))
    if canonical:
        answer = answer.rstrip() + "\n\nNguồn: " + ", ".join(f"[{item}]" for item in canonical)
    return answer


# Retain the established import name for existing callers and tests.
synthesize = synthesize_completed_results
