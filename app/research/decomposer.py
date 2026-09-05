from __future__ import annotations
import json
import re
from app.core.types import Task, RunMetrics


def _extract_json(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            raise ValueError("Planner did not return JSON")
        return json.loads(m.group(0))

async def decompose(provider, query: str, planning_context: str, metrics: RunMetrics) -> list[Task]:
    system = "TASK_DECOMPOSER. Return JSON only. Preserve atomic obligations and dependencies. Do not invent requirements."
    user = f"USER REQUEST:\n{query}\n\nPLANNING CONTEXT:\n{planning_context}\n\nSchema: {{\"tasks\":[{{\"id\":\"T1\",\"goal\":\"...\",\"domain\":\"security|database|api_architecture\",\"depends_on\":[],\"evidence_needs\":[]}}]}}"
    result = await provider.generate(system=system, user=user)
    metrics.add_usage(result.usage)
    obj = _extract_json(result.text)
    tasks = []
    for i, raw in enumerate(obj.get("tasks") or []):
        tasks.append(Task(
            task_id=str(raw.get("id") or f"T{i+1}"),
            goal=str(raw.get("goal") or query),
            domain=str(raw.get("domain") or "api_architecture"),
            depends_on=[str(x) for x in raw.get("depends_on") or []],
            evidence_needs=[str(x) for x in raw.get("evidence_needs") or []],
        ))
    return tasks or [Task(task_id="T1", goal=query)]
