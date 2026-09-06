from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.providers.factory import get_provider
from app.research.p_lite_pipeline import PLitePipeline
from app.research.pipeline import ResearchPipeline
from app.storage.run_store import RunStore
from app.storage.source_store import SourceStore


ROOT = Path(__file__).resolve().parents[2]


@dataclass
class PLitePipelineService:
    """Resolve a local provider before invoking the inspection-only pipeline."""

    pipeline: PLitePipeline

    async def __call__(self, request: str, provider_name: str | None = None) -> Any:
        return await self.pipeline.run(request, get_provider(provider_name))


@dataclass
class ApiRuntime:
    """Application services owned by the HTTP boundary.

    Keeping these services on the app state makes the API testable without
    creating a second global pipeline, while preserving the existing M0
    stores and pipeline contracts.
    """

    source_store: SourceStore
    run_store: RunStore
    pipeline: ResearchPipeline
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
        run_store = RunStore(str(runs_root))
        return cls(
            source_store=source_store,
            run_store=run_store,
            pipeline=ResearchPipeline(source_store, run_store),
            p_lite_pipeline=PLitePipelineService(PLitePipeline()),
        )
