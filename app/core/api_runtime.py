from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.providers.factory import get_provider
from app.research.p_lite_pipeline import PLitePipeline
from app.research.pipeline import ResearchPipeline
from app.run.coordinator import RunCoordinator
from app.storage.knowledge_base import KnowledgeBase
from app.storage.conversation_store import ConversationStore
from app.storage.run_store import RunStore
from app.storage.source_store import SourceStore


ROOT = Path(__file__).resolve().parents[2]


@dataclass
class PLitePipelineService:
    """Resolve a local provider before invoking the inspection-only pipeline."""

    pipeline: PLitePipeline

    async def __call__(self, request: str, provider_name: str | None = None) -> Any:
        result = await self.pipeline.run(request, get_provider(provider_name))
        return result.to_dict()


@dataclass
class ApiRuntime:
    """Application services owned by the HTTP boundary.

    Keeping these services on the app state makes the API testable without
    creating a second global pipeline, while preserving the existing M0
    stores and pipeline contracts.
    """

    source_store: SourceStore
    knowledge_base: KnowledgeBase
    run_store: RunStore
    conversation_store: ConversationStore
    pipeline: ResearchPipeline
    run_coordinator: RunCoordinator
    p_lite_pipeline: PLitePipelineService

    @classmethod
    def from_env(
        cls,
        *,
        data_dir: str | Path | None = None,
        runs_dir: str | Path | None = None,
    ) -> "ApiRuntime":
        data_root = data_dir if data_dir is not None else os.getenv("APP_DATA_DIR", str(ROOT / "data"))
        runs_root = runs_dir if runs_dir is not None else os.getenv("RUNS_DIR", str(ROOT / "runs"))
        source_store = SourceStore(str(data_root))
        knowledge_base = KnowledgeBase.from_env(source_store)
        run_store = RunStore(str(runs_root))
        conversation_store = ConversationStore(Path(data_root) / "conversations")
        pipeline = ResearchPipeline(
            source_store,
            run_store,
            knowledge_base=knowledge_base,
        )
        return cls(
            source_store=source_store,
            knowledge_base=knowledge_base,
            run_store=run_store,
            conversation_store=conversation_store,
            pipeline=pipeline,
            run_coordinator=pipeline.run_coordinator,
            p_lite_pipeline=PLitePipelineService(PLitePipeline()),
        )
