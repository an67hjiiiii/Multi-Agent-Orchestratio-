from app.core.types import SourceChunk
from app.research.context_controller import ContextController
from app.retrieval.text import estimate_tokens


def test_token_budget_keeps_ranked_chunks_and_accounts_drops():
    chunks = [
        SourceChunk('c1', 's', 'x', 'a' * 15, 0, 1.0),
        SourceChunk('c2', 's', 'x', 'b' * 15, 1, 0.9),
        SourceChunk('c3', 's', 'x', 'c' * 15, 2, 0.8),
    ]

    selected, dropped = ContextController(max_tokens=10).select(chunks)

    assert [chunk.chunk_id for chunk in selected] == ['c1', 'c2']
    assert sum(estimate_tokens(chunk.text) for chunk in selected) <= 10
    assert [record['chunk_id'] for record in dropped] == ['c3']
    assert dropped[0]['reason'] == 'budget_exceeded'
    assert dropped[0]['estimated_tokens'] == 5
    assert dropped[0]['allocated_tokens'] == 0


def test_oversized_first_chunk_is_truncated_within_hard_cap():
    chunks = [
        SourceChunk('large', 's', 'x', 'abcdef', 0, 1.0),
        SourceChunk('next', 's', 'x', 'z', 1, 0.9),
    ]

    selected, dropped = ContextController(max_tokens=1).select(chunks)

    assert [chunk.chunk_id for chunk in selected] == ['large']
    assert selected[0].text == 'abc'
    assert sum(estimate_tokens(chunk.text) for chunk in selected) <= 1
    assert dropped[0] == {
        'chunk_id': 'large',
        'reason': 'truncated_to_hard_context_token_cap',
        'estimated_tokens': 2,
        'allocated_tokens': 1,
    }
    assert dropped[1]['chunk_id'] == 'next'
    assert dropped[1]['reason'] == 'budget_exceeded'


def test_exact_duplicates_are_dropped_deterministically():
    chunks = [
        SourceChunk('c2', 's', 'x', 'same', 1, 0.8),
        SourceChunk('c1', 's', 'x', ' same ', 0, 0.8),
        SourceChunk('c3', 's', 'x', 'different', 2, 0.7),
    ]

    selected, dropped = ContextController(max_tokens=20).select(chunks)

    assert [chunk.chunk_id for chunk in selected] == ['c1', 'c3']
    assert [record['chunk_id'] for record in dropped] == ['c2']
    assert dropped[0]['reason'] == 'exact_duplicate'


def test_zero_budget_never_selects_nonempty_evidence():
    chunks = [SourceChunk('c1', 's', 'x', 'evidence', 0, 1.0)]

    selected, dropped = ContextController(max_tokens=0).select(chunks)

    assert selected == []
    assert dropped[0]['chunk_id'] == 'c1'
    assert dropped[0]['reason'] == 'budget_exceeded'
