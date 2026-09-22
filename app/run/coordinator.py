"""Application-level coordination for the persisted Run lifecycle.

The coordinator deliberately owns request-to-run orchestration and persistence.
It receives the existing processing callbacks so P/N/O, retrieval, workers, and
synthesis stay in ``ResearchPipeline`` rather than being moved here.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from app.core.config import CONDITION_DEFINITIONS, RuntimeConfig
from app.core.telemetry import gpu_memory_mb, process_rss_mb
from app.core.types import RunMetrics, Task, TaskResult
from app.research.conversation_context import ConversationContext
from app.run.contracts import Run


ProcessingCallback = Callable[
    [
        str,
        str,
        Any,
        RuntimeConfig,
        dict[str, bool],
        ConversationContext,
        RunMetrics,
        Callable[..., None],
        dict[str, Any],
    ],
    Awaitable[tuple[str, str, list[Task], list[TaskResult], bool]],
]
MetadataCallback = Callable[[], Awaitable[dict[str, Any]]]


class RunCoordinator:
    """Create, finalize, and persist product Runs around existing processing."""

    def __init__(
        self,
        source_store: Any,
        run_store: Any,
        *,
        process: ProcessingCallback,
        retrieval_metadata: MetadataCallback,
        provider_resolver: Callable[[str | None], Any],
        scoring_versions: dict[str, Any],
        planning_retrieval_scoring_version: str,
        retrieval_scoring_version: str,
        domain_ranking_version: str,
        retrieval_metadata_defaults: dict[str, Any],
    ) -> None:
        self.source_store = source_store
        self.run_store = run_store
        self._process = process
        self._retrieval_metadata = retrieval_metadata
        self._provider_resolver = provider_resolver
        self._scoring_versions = dict(scoring_versions)
        self._planning_retrieval_scoring_version = planning_retrieval_scoring_version
        self._retrieval_scoring_version = retrieval_scoring_version
        self._domain_ranking_version = domain_ranking_version
        self._retrieval_metadata_defaults = dict(retrieval_metadata_defaults)

    async def execute(
        self,
        query: str,
        condition: str = "A",
        provider_name: str | None = None,
        *,
        conversation_context: ConversationContext | str | None = None,
        conversation_id: str | None = None,
    ) -> dict[str, Any]:
        """Coordinate one request through the existing processing pipeline."""

        condition = condition.upper()
        definition = CONDITION_DEFINITIONS.get(condition)
        if definition is None:
            raise ValueError(f"Unknown condition {condition}")
        if isinstance(conversation_context, str):
            conversation_context = ConversationContext(text=conversation_context)
        elif not isinstance(conversation_context, ConversationContext):
            conversation_context = ConversationContext()

        cfg = RuntimeConfig.from_env()
        cfg.assert_condition(condition)
        provider = self._provider_resolver(provider_name)
        started = time.perf_counter()
        metrics = RunMetrics(peak_rss_mb=process_rss_mb(), gpu_memory_mb=gpu_memory_mb())
        events: list[dict[str, Any]] = []
        run_id = "run_" + uuid.uuid4().hex[:12]
        flags = {flag: bool(definition[flag]) for flag in ("P", "N", "O")}
        source_snapshot = self.source_store.snapshot_id()

        def event(stage: str, **data: Any) -> None:
            events.append({"stage": stage, "ts": datetime.now(timezone.utc).isoformat(), **data})

        def finalize(
            status: str,
            answer: str,
            tasks: list[Task],
            task_results: list[TaskResult],
            retrieval_metadata: dict[str, Any],
        ) -> dict[str, Any]:
            metrics.latency_ms = int((time.perf_counter() - started) * 1000)
            metrics.peak_rss_mb = max(
                filter(lambda value: value is not None, [metrics.peak_rss_mb, process_rss_mb()]),
                default=None,
            )
            metrics.gpu_memory_mb = gpu_memory_mb()
            effective = {
                "condition": condition,
                "implementation_profile": cfg.implementation_profile,
                "flags": flags,
                "task_top_k": cfg.task_top_k,
                "planning_top_k": cfg.planning_top_k,
                "max_context_tokens": cfg.max_context_tokens,
                "max_output_tokens": cfg.max_output_tokens,
                "max_run_tokens": cfg.max_run_tokens,
                "retry_limit": cfg.retry_limit,
                "conversation_id": conversation_id,
                "conversation_context": conversation_context.to_trace(),
                "retrieval_min_score": cfg.retrieval_min_score,
                "scoring_versions": dict(self._scoring_versions),
                "retrieval": dict(retrieval_metadata),
            }
            run = {
                "run_id": run_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "condition": condition,
                "implementation_profile": cfg.implementation_profile,
                "provider": provider.name,
                "model": provider.model,
                "query": query,
                "conversation_id": conversation_id,
                "conversation_context": conversation_context.to_trace(),
                "status": status,
                "answer": answer,
                "source_snapshot_id": source_snapshot,
                "config_hash": cfg.config_hash(),
                "tasks": [asdict(task) for task in tasks],
                "task_results": [asdict(result) for result in task_results],
                "metrics": metrics.to_dict(),
                "events": events,
                "effective_config": effective,
                "scoring_versions": dict(self._scoring_versions),
                "planning_retrieval_scoring_version": self._planning_retrieval_scoring_version,
                "retrieval_scoring_version": self._retrieval_scoring_version,
                "domain_ranking_version": self._domain_ranking_version,
                "retrieval": dict(retrieval_metadata),
            }
            typed_run = Run.from_mapping(run)
            self.run_store.save(typed_run)
            return typed_run.to_dict()

        try:
            retrieval_metadata = await self._retrieval_metadata()
        except Exception as exc:
            retrieval_metadata = {
                **self._retrieval_metadata_defaults,
                "retrieval_backend": "unavailable",
            }
            event(
                "run_started",
                condition=condition,
                provider=provider.name,
                model=provider.model,
                implementation_profile=cfg.implementation_profile,
                source_snapshot_id=source_snapshot,
                config_hash=cfg.config_hash(),
                flags=flags,
                scoring_versions=dict(self._scoring_versions),
                retrieval=dict(retrieval_metadata),
            )
            event("retrieval_failed", error_type=type(exc).__name__)
            return finalize(
                "FAILED",
                f"Pipeline failed: retrieval metadata unavailable ({type(exc).__name__})",
                [],
                [],
                retrieval_metadata,
            )

        event(
            "run_started",
            condition=condition,
            provider=provider.name,
            model=provider.model,
            implementation_profile=cfg.implementation_profile,
            source_snapshot_id=source_snapshot,
            config_hash=cfg.config_hash(),
            flags=flags,
            scoring_versions=dict(self._scoring_versions),
            retrieval=dict(retrieval_metadata),
        )
        event(
            "conversation_context",
            current_request=query,
            **conversation_context.to_trace(),
        )
        try:
            status, answer, tasks, task_results, emit_finished = await self._process(
                query,
                condition,
                provider,
                cfg,
                flags,
                conversation_context,
                metrics,
                event,
                retrieval_metadata,
            )
            if emit_finished:
                event("run_finished", status=status)
            return finalize(status, answer, tasks, task_results, retrieval_metadata)
        except Exception as exc:
            event("run_failed", error_type=type(exc).__name__, error=str(exc))
            return finalize(
                "FAILED",
                f"Pipeline failed: {type(exc).__name__}: {exc}",
                [],
                [],
                retrieval_metadata,
            )


__all__ = ["RunCoordinator"]
