from app.core.types import SourceChunk
from app.retrieval.text import apply_token_budget, estimate_tokens


def test_hard_context_budget():
    chunks=[
        SourceChunk('c1','s','x','a '*200,0,1.0),
        SourceChunk('c2','s','x','b '*200,1,0.9),
    ]
    selected,dropped=apply_token_budget(chunks,100)
    assert selected
    assert sum(estimate_tokens(c.text) for c in selected) <= 110
    assert dropped
