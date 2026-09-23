"""Stable composition seams for local research and evaluation tooling.

The HTTP application owns its own runtime composition.  This module provides
the corresponding narrow boundary for serial research runners so evaluation
code does not reach through scripts to assemble stores and pipelines.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.research.pipeline import ResearchPipeline
    from app.storage.source_store import SourceStore


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS_DIR = ROOT / "datasets" / "domain"


def prepare_source_store(
    data_dir: str | Path,
    corpus_dir: str | Path = DEFAULT_CORPUS_DIR,
) -> SourceStore:
    """Build a fresh deterministic source store from the local corpus.

    This is the shared application boundary used by evaluation and research
    runners.  It intentionally retains the existing clear-and-import
    semantics of the M0 calibration helper.
    """

    from app.storage.source_store import SourceStore

    data_path = Path(data_dir)
    corpus_path = Path(corpus_dir)
    source_files = sorted(corpus_path.glob("*.md"), key=lambda item: item.name)
    if not source_files:
        raise ValueError(f"No Markdown calibration sources found in {corpus_path}")

    store = SourceStore(str(data_path))
    store.clear()
    for source_path in source_files:
        store.import_text(source_path.name, source_path.read_text(encoding="utf-8"))
    return store


def build_research_pipeline(
    source_store: SourceStore,
    runs_dir: str | Path,
    *,
    knowledge_base: Any | None = None,
    retriever: Any | None = None,
) -> ResearchPipeline:
    """Compose a research pipeline with an isolated run store.

    ``ResearchPipeline`` remains the compatibility and processing API; this
    function only centralizes the construction boundary used by serial tools.
    """

    from app.research.pipeline import ResearchPipeline
    from app.storage.run_store import RunStore

    return ResearchPipeline(
        source_store,
        RunStore(str(runs_dir)),
        knowledge_base=knowledge_base,
        retriever=retriever,
    )


def build_pipeline_from_corpus(
    *,
    data_dir: str | Path,
    runs_dir: str | Path,
    corpus_dir: str | Path = DEFAULT_CORPUS_DIR,
) -> ResearchPipeline:
    """Prepare an isolated corpus store and compose its research pipeline."""

    return build_research_pipeline(
        prepare_source_store(data_dir=data_dir, corpus_dir=corpus_dir),
        runs_dir,
    )


__all__ = [
    "DEFAULT_CORPUS_DIR",
    "build_pipeline_from_corpus",
    "build_research_pipeline",
    "prepare_source_store",
]
