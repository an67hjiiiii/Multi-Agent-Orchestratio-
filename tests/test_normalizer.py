from app.core.types import Task
from app.research.normalizer import normalize_tasks, normalize_tasks_with_trace

def test_conservative_duplicate_removal():
    tasks=[Task('T1','Review JWT authentication','security'),Task('T2','Review JWT authentication','security'),Task('T3','Review SQL query','database')]
    normalized,removed=normalize_tasks(tasks)
    assert removed==1
    assert len(normalized)==2


def test_rules_only_keeps_similar_security_obligations_separate_and_preserves_fields():
    tasks = [
        Task("T1", "Review authentication", "security", object="identity", action="review", deliverable="auth findings", requirement_ids=["R1"], constraints=["local"]),
        Task("T2", "Review authorization", "security", object="permission", action="review", deliverable="authz findings", requirement_ids=["R2"], constraints=["local"], depends_on=["T1"]),
    ]
    normalized, trace = normalize_tasks_with_trace(tasks)
    assert [task.task_id for task in normalized] == ["T1", "T2"]
    assert normalized[1].depends_on == ["T1"]
    assert normalized[0].requirement_ids == ["R1"]
    assert all(item["decision"] == "KEEP" for item in trace)


def test_exact_duplicate_merges_and_remaps_a_dependent_task_without_losing_dependency():
    tasks = [
        Task("T1", "Review authentication", "security", object="identity", action="review", deliverable="findings"),
        Task("T2", "Review authentication", "security", object="identity", action="review", deliverable="findings"),
        Task("T3", "Review authorization", "security", depends_on=["T2"]),
    ]
    normalized, trace = normalize_tasks_with_trace(tasks)
    assert [task.task_id for task in normalized] == ["T1", "T3"]
    assert normalized[1].depends_on == ["T1"]
    assert any(item["decision"] == "MERGE" and item["task_id"] == "T2" for item in trace)


def test_merge_that_would_create_self_dependency_rolls_back():
    tasks = [
        Task("T1", "Review authentication", "security", object="identity", action="review", deliverable="findings"),
        Task("T2", "Review authentication", "security", depends_on=["T1"], object="identity", action="review", deliverable="findings"),
    ]
    normalized, trace = normalize_tasks_with_trace(tasks)
    assert normalized == tasks
    assert trace[-1]["decision"] == "ROLLBACK"
