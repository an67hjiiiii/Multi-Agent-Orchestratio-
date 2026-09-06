from __future__ import annotations
import json

from app.core.citations import resolve_citation_ids
from app.core.types import TaskResult, RunMetrics


def _json_object(text: str) -> dict:
    try:
        value = json.loads(text)
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}

async def synthesize(provider, query: str, results: list[TaskResult], metrics: RunMetrics) -> str:
    compact = []
    available_ids: list[str] = []
    worker_citations: list[str] = []
    for r in results:
        available_ids.extend(r.evidence_ids)
        worker_citations.extend(r.citations)
        compact.append(
            f"TASK {r.task_id} [{r.domain}] status={r.status}\n"
            f"answer={r.answer}\n"
            f"worker_citations={','.join(r.citations)}\n"
            f"available_evidence={','.join(r.evidence_ids)}\n"
            f"missing={','.join(r.missing_information)}"
        )
    system = (
        "SYNTHESIZER. Combine structured task results. Do not invent evidence or new facts. "
        "Return JSON only: {\"answer\":\"...\",\"citations\":[\"E1\"]}. "
        "Citations may contain only supplied E-keys; say when a task is PARTIAL/NO_EVIDENCE."
    )
    evidence_keys = "\n".join(f"E{index}={item}" for index, item in enumerate(dict.fromkeys(available_ids), start=1))
    user = f"USER REQUEST:\n{query}\n\nAVAILABLE EVIDENCE KEYS:\n{evidence_keys}\n\nTASK RESULTS:\n" + "\n\n".join(compact)
    result = await provider.generate(system=system, user=user)
    metrics.add_usage(result.usage)
    payload = _json_object(result.text)
    answer = payload.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        answer = "\n\n".join(f"{item.task_id}: {item.answer}" for item in results).strip()
    synthesis_valid, synthesis_invalid = resolve_citation_ids(payload.get("citations"), available_ids)
    worker_valid, _ = resolve_citation_ids(worker_citations, available_ids)
    metrics.add_citations(synthesis_valid, synthesis_invalid)
    canonical = list(dict.fromkeys([*worker_valid, *synthesis_valid]))
    if canonical:
        answer = answer.rstrip() + "\n\nNguồn: " + ", ".join(f"[{item}]" for item in canonical)
    return answer
