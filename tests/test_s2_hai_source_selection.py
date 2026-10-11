from __future__ import annotations

import asyncio

from app.research.pipeline import ResearchPipeline
from app.storage.run_store import RunStore
from app.storage.source_store import SourceStore


def test_pipeline_retrieves_only_explicit_source_selection(tmp_path, monkeypatch):
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "m0")
    sources = SourceStore(str(tmp_path / "data"))
    selected = sources.import_text("selected.md", "The selected source contains API evidence.")
    sources.import_text("other.md", "The other source contains unrelated evidence.")
    run = asyncio.run(
        ResearchPipeline(sources, RunStore(str(tmp_path / "runs"))).run(
            "What evidence is available?",
            "A",
            "fake",
            source_ids=[selected["source_id"]],
        )
    )
    retrieval = next(event for event in run["events"] if event["stage"] == "vanilla_retrieval")
    assert all(chunk_id.startswith(selected["source_id"] + "_") for chunk_id in retrieval["candidates"])


def test_pipeline_rejects_source_selection_outside_owner_store(tmp_path, monkeypatch):
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "m0")
    sources = SourceStore(str(tmp_path / "data"))
    sources.import_text("owned.md", "Owned evidence.")
    try:
        asyncio.run(
            ResearchPipeline(sources, RunStore(str(tmp_path / "runs"))).run(
                "Question", "A", "fake", source_ids=["src_foreign"]
            )
        )
    except LookupError as exc:
        assert str(exc) == "source not found"
    else:
        raise AssertionError("foreign source selection must fail closed")
