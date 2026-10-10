from __future__ import annotations
from collections import defaultdict, deque
from app.core.types import Task


def validate_tasks(tasks: list[Task]) -> None:
    ids = [t.task_id for t in tasks]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate task_id")
    known = set(ids)
    indeg = {task_id: 0 for task_id in ids}
    edges: dict[str, list[str]] = defaultdict(list)
    for task in tasks:
        for dep in task.depends_on:
            if dep not in known:
                raise ValueError(f"Unknown dependency: {dep}")
            if dep == task.task_id:
                raise ValueError("Self dependency")
            edges[dep].append(task.task_id)
            indeg[task.task_id] += 1
    queue = deque([task_id for task_id, degree in indeg.items() if degree == 0])
    seen: list[str] = []
    while queue:
        current = queue.popleft()
        seen.append(current)
        for nxt in edges[current]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
    if len(seen) != len(ids):
        raise ValueError("Task graph contains a cycle")


def topological_order(tasks: list[Task]) -> list[Task]:
    validate_tasks(tasks)
    by_id = {t.task_id: t for t in tasks}
    done: set[str] = set()
    ordered: list[Task] = []
    while len(ordered) < len(tasks):
        ready = [t for t in tasks if t.task_id not in done and all(d in done for d in t.depends_on)]
        if not ready:
            raise ValueError("No ready task; invalid dependency graph")
        for task in ready:
            ordered.append(by_id[task.task_id])
            done.add(task.task_id)
    return ordered
