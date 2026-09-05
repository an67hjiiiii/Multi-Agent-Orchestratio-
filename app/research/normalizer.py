from __future__ import annotations
import re
from app.core.types import Task


def _fingerprint(task: Task) -> set[str]:
    return set(re.findall(r"[A-Za-zÀ-ỹ0-9_]{2,}", task.goal.lower()))


def normalize_tasks(tasks: list[Task]) -> tuple[list[Task], int]:
    """Conservative S0 normalizer: exact/near-exact duplicate removal only.

    Full semantic MERGE/KEEP/NARROW belongs to M2, not S0.
    """
    kept: list[Task] = []
    removed = 0
    for task in tasks:
        fp = _fingerprint(task)
        duplicate = False
        for prev in kept:
            if task.domain != prev.domain:
                continue
            prev_fp = _fingerprint(prev)
            if fp == prev_fp or (fp and prev_fp and len(fp & prev_fp) / max(1, min(len(fp), len(prev_fp))) >= 0.92):
                duplicate = True
                removed += 1
                break
        if not duplicate:
            kept.append(task)
    # re-number only when IDs collided/removed; remap dependencies conservatively
    old_to_new: dict[str, str] = {}
    for i, task in enumerate(kept, 1):
        old_to_new[task.task_id] = f"T{i}"
    normalized: list[Task] = []
    for task in kept:
        normalized.append(Task(
            task_id=old_to_new[task.task_id],
            goal=task.goal,
            domain=task.domain,
            depends_on=[old_to_new[d] for d in task.depends_on if d in old_to_new],
            evidence_needs=task.evidence_needs,
        ))
    return normalized, removed
