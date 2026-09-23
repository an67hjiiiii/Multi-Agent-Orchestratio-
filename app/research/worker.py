from __future__ import annotations
from app.core.types import Task, TaskResult, SourceChunk, RunMetrics
from app.orchestration.routing import worker_profile
from app.research.contracts import WorkerResult
from app.research.verification import verify_worker_response

async def execute_task(provider, task: Task, evidence: list[SourceChunk], metrics: RunMetrics) -> WorkerResult:
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
    p = worker_profile(task.domain)
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
    return verify_worker_response(result.text, task, evidence, metrics)
