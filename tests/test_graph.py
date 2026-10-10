import pytest
from app.core.graph import validate_tasks, topological_order
from app.core.types import Task

def test_valid_graph():
    tasks=[Task('T1','a'),Task('T2','b',depends_on=['T1'])]
    validate_tasks(tasks)
    assert [t.task_id for t in topological_order(tasks)]==['T1','T2']

def test_cycle_rejected():
    with pytest.raises(ValueError):
        validate_tasks([Task('T1','a',depends_on=['T2']),Task('T2','b',depends_on=['T1'])])
