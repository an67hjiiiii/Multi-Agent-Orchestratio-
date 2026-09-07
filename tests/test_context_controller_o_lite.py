from app.core.types import SourceChunk
from app.research.context_controller import ContextController, OverlapTracker


def _chunk(chunk_id, source_id, text, score=1.0, index=0):
    return SourceChunk(chunk_id, source_id, source_id + ".md", text, index, score)


def test_o_lite_removes_same_source_overlap_and_keeps_shared_evidence_per_task():
    chunks = [
        _chunk("c1", "s1", "Authentication identity verification evidence", index=0),
        _chunk("c2", "s1", "Authentication identity verification evidence with more detail", index=1),
        _chunk("c3", "s2", "Authentication identity verification evidence", index=0),
    ]
    selected, dropped, selected_log = ContextController(max_tokens=100).select_for_task(
        chunks, task_terms={"authentication", "identity"}, max_tokens=100
    )
    assert {chunk.chunk_id for chunk in selected} == {"c1"}
    assert any(item["reason"] == "overlapping_span" and item["chunk_id"] == "c2" for item in dropped)
    assert selected_log[0]["source_id"] == "s1"
    second_selected, _, _ = ContextController(max_tokens=100).select_for_task(
        [chunks[0]], task_terms={"authentication", "identity"}, max_tokens=100
    )
    assert [chunk.chunk_id for chunk in second_selected] == ["c1"]


def test_o_lite_logs_low_relevance_without_running_semantic_dedup():
    selected, dropped, _ = ContextController(max_tokens=100).select_for_task(
        [_chunk("c1", "s1", "Database indexes", score=0.5)],
        task_terms={"authentication"}, max_tokens=100,
    )
    assert selected == []
    assert dropped[0]["reason"] == "low_relevance"


def test_overlap_tracker_keeps_legitimate_shared_evidence_and_reports_reuse():
    tracker = OverlapTracker()
    evidence = _chunk("c1", "s1", "Authentication identity verification evidence")
    first = tracker.observe("T1", [evidence])
    second = tracker.observe("T2", [evidence])
    assert first["shared_evidence_ids"] == []
    assert second["shared_evidence_ids"] == ["c1"]
    assert second["reused_from_task_ids"] == {"c1": ["T1"]}
    assert tracker.summary()["reuse_by_evidence_id"] == {"c1": ["T1", "T2"]}


def test_local_selection_does_not_claim_cross_task_sharing_before_tracker_observes_reuse():
    selected, _, selected_log = ContextController(max_tokens=100).select_for_task(
        [_chunk("c1", "s1", "Authentication identity verification evidence")],
        task_terms={"authentication", "identity"},
        max_tokens=100,
    )

    assert [chunk.chunk_id for chunk in selected] == ["c1"]
    assert selected_log == [{
        "chunk_id": "c1", "source_id": "s1", "locator": 0,
        "score": 1.0, "reason": "retained",
    }]
