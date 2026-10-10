from app.core.types import Task
from app.research.normalizer import normalize_tasks

def test_conservative_duplicate_removal():
    tasks=[Task('T1','Review JWT authentication','security'),Task('T2','Review JWT authentication','security'),Task('T3','Review SQL query','database')]
    normalized,removed=normalize_tasks(tasks)
    assert removed==1
    assert len(normalized)==2
