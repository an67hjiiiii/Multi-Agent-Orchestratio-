from __future__ import annotations
import inspect
import time
import uuid
from collections.abc import Callable, Mapping
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any
from app.core.config import CONDITION_DEFINITIONS, RuntimeConfig
from app.core.graph import topological_order, validate_tasks
from app.core.telemetry import process_rss_mb, gpu_memory_mb
from app.core.types import SourceChunk, Task, TaskResult, RunMetrics
from app.providers.factory import get_provider
from app.research.context_controller import ContextController, OverlapTracker
from app.research.conversation_context import ConversationContext
from app.research.decomposer import decompose
from app.research.normalizer import normalize_tasks_with_trace
from app.research.planning_retrieval import (
    PLANNING_RETRIEVAL_SCORING_VERSION,
    PlanningRetriever,
)
from app.research.worker import execute_task
from app.research.synthesizer import synthesize
from app.research.vanilla import answer_vanilla
from app.retrieval.text import (
    DOMAIN_RANKING_VERSION,
    RETRIEVAL_SCORING_VERSION,
    apply_token_budget,
    estimate_context_tokens,
    retrieve,
    terms,
)
from app.storage.source_store import SourceStore
from app.storage.run_store import RunStore

CONDITIONS = {"A", "B", "C", "C-P", "C-N", "C-O"}
TASK_QUERY_FORMULATION_VERSION = "task-query-v2-anchor-preserving"
TASK_QUERY_FALLBACK_REASON = "task_query_no_results_fallback_to_user_request"
TASK_QUERY_DOMAIN_FALLBACK_REASON = "task_query_no_results_fallback_to_task_domain"
SCORING_VERSION_METADATA = {
    "planning_retrieval": PLANNING_RETRIEVAL_SCORING_VERSION,
    "answer_retrieval": RETRIEVAL_SCORING_VERSION,
    "domain_ranking": DOMAIN_RANKING_VERSION,
}
_RETRIEVAL_METADATA_DEFAULTS = {
    "retrieval_backend": "lexical",
    "index_version": None,
    "embedding_version": None,
    "embedding_model": None,
    "embedding_digest": None,
    "embedding_dimension": None,
    "corpus_snapshot_id": None,
    "collection": None,
    "readiness": "ready",
    "retrieval_scoring_version": RETRIEVAL_SCORING_VERSION,
    "domain_ranking_version": DOMAIN_RANKING_VERSION,
}
_RETRIEVAL_METADATA_FIELDS = frozenset(_RETRIEVAL_METADATA_DEFAULTS)
_RETRIEVAL_METADATA_SCALAR_TYPES = (bool, int, float, str)

class ResearchPipeline:
    def __init__(
        self,
        source_store: SourceStore,
        run_store: RunStore,
        *,
        knowledge_base: Any | None = None,
        retriever: Any | None = None,
    ):
        if knowledge_base is not None and retriever is not None:
            raise ValueError("pass either knowledge_base or retriever, not both")
        self.source_store = source_store
        self.run_store = run_store
        self.knowledge_base = knowledge_base
        self.retrieval_owner = retriever if retriever is not None else knowledge_base
        self.retriever = _preferred_retriever(self.retrieval_owner)
        self.planning = PlanningRetriever()

    async def run(
        self,
        query: str,
        condition: str = "A",
        provider_name: str | None = None,
        *,
        conversation_context: ConversationContext | str | None = None,
        conversation_id: str | None = None,
    ) -> dict:
        condition = condition.upper()
        if condition not in CONDITIONS:
            raise ValueError(f"Unknown condition {condition}")
        if isinstance(conversation_context, str):
            conversation_context = ConversationContext(text=conversation_context)
        elif not isinstance(conversation_context, ConversationContext):
            conversation_context = ConversationContext()
        cfg = RuntimeConfig.from_env()
        cfg.assert_condition(condition)
        provider = get_provider(provider_name)
        started = time.perf_counter()
        metrics = RunMetrics(peak_rss_mb=process_rss_mb(), gpu_memory_mb=gpu_memory_mb())
        events: list[dict] = []
        run_id = "run_" + uuid.uuid4().hex[:12]
        flags = self._flags(condition)
        source_snapshot = self.source_store.snapshot_id()

        def event(stage: str, **data):
            events.append({"stage": stage, "ts": datetime.now(timezone.utc).isoformat(), **data})

        def finalize(status: str, answer: str, tasks: list[Task], task_results: list[TaskResult]) -> dict:
            metrics.latency_ms = int((time.perf_counter() - started) * 1000)
            metrics.peak_rss_mb = max(filter(lambda x: x is not None, [metrics.peak_rss_mb, process_rss_mb()]), default=None)
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
                "scoring_versions": dict(SCORING_VERSION_METADATA),
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
                "tasks": [asdict(t) for t in tasks],
                "task_results": [asdict(r) for r in task_results],
                "metrics": metrics.to_dict(),
                "events": events,
                "effective_config": effective,
                "scoring_versions": dict(SCORING_VERSION_METADATA),
                "planning_retrieval_scoring_version": PLANNING_RETRIEVAL_SCORING_VERSION,
                "retrieval_scoring_version": RETRIEVAL_SCORING_VERSION,
                "domain_ranking_version": DOMAIN_RANKING_VERSION,
                "retrieval": dict(retrieval_metadata),
            }
            self.run_store.save(run)
            return run

        try:
            retrieval_metadata = await self._retrieval_metadata()
        except Exception as exc:
            retrieval_metadata = {
                **_RETRIEVAL_METADATA_DEFAULTS,
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
                scoring_versions=dict(SCORING_VERSION_METADATA),
                retrieval=dict(retrieval_metadata),
            )
            event("retrieval_failed", error_type=type(exc).__name__)
            return finalize(
                "FAILED",
                f"Pipeline failed: retrieval metadata unavailable ({type(exc).__name__})",
                [],
                [],
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
            scoring_versions=dict(SCORING_VERSION_METADATA),
            retrieval=dict(retrieval_metadata),
        )
        event(
            "conversation_context",
            current_request=query,
            **conversation_context.to_trace(),
        )
        all_chunks = self.source_store.chunks()
        try:
            if condition == "A":
                r0 = time.perf_counter()
                candidates = await self._retrieve(
                    _retrieval_query_with_conversation_context(query, conversation_context),
                    all_chunks,
                    top_k=cfg.task_top_k,
                    min_score=cfg.retrieval_min_score,
                )
                metrics.retrieval_latency_ms += int((time.perf_counter() - r0) * 1000)
                metrics.retrieved_chunks += len(candidates)
                selected, budget_dropped = apply_token_budget(candidates, cfg.max_context_tokens)
                metrics.selected_chunks += len(selected)
                metrics.dropped_chunks += len(budget_dropped)
                metrics.context_chars += sum(len(c.text) for c in selected)
                context_tokens = estimate_context_tokens(selected)
                metrics.context_tokens_est += context_tokens
                event(
                    "vanilla_retrieval",
                    candidates=[c.chunk_id for c in candidates],
                    selected=[c.chunk_id for c in selected],
                    dropped=budget_dropped,
                    context_tokens=context_tokens,
                    scoring_version=RETRIEVAL_SCORING_VERSION,
                    retrieval=dict(retrieval_metadata),
                )
                task = Task(task_id="T1", goal=query, domain="general")
                g0 = time.perf_counter()
                result = await answer_vanilla(provider, query, selected, metrics)
                metrics.generation_latency_ms += int((time.perf_counter() - g0) * 1000)
                tasks, task_results = [task], [result]
                answer = result.answer
            else:
                planning_context = ""
                if flags["P"]:
                    planning_hits = self.planning.search(query, top_k=cfg.planning_top_k)
                    planning_context = "\n\n".join(f"[{c.chunk_id}] {c.text}" for c in planning_hits)
                    event(
                        "planning_retrieval",
                        selected=[c.chunk_id for c in planning_hits],
                        scoring_version=PLANNING_RETRIEVAL_SCORING_VERSION,
                    )
                g0 = time.perf_counter()
                decomposition = await decompose(
                    provider,
                    query,
                    planning_context,
                    metrics,
                    conversation_context=conversation_context.text,
                )
                tasks = _runtime_tasks(decomposition)
                metrics.generation_latency_ms += int((time.perf_counter() - g0) * 1000)
                event(
                    "decomposition",
                    tasks=[asdict(t) for t in tasks],
                    required_obligations=_obligation_trace_records(decomposition),
                    task_obligation_coverage=_task_obligation_coverage(decomposition),
                    covered_obligations=list(
                        getattr(decomposition, "covered_obligations", [])
                    ),
                    missing_obligations=list(
                        getattr(decomposition, "missing_obligations", [])
                    ),
                    repair_attempted=bool(
                        getattr(decomposition, "repair_attempted", False)
                    ),
                    coverage_validation_reason=getattr(
                        decomposition,
                        "coverage_validation_reason",
                        None,
                    ),
                )
                if getattr(decomposition, "status", "COMPLETE") != "COMPLETE" or not tasks:
                    event(
                        "decomposition_failed",
                        warnings=list(getattr(decomposition, "warnings", [])),
                    )
                    return finalize(
                        "FAILED",
                        "Pipeline failed: decomposer returned no valid tasks",
                        [],
                        [],
                    )
                if flags["N"]:
                    task_count_before_normalization = len(tasks)
                    tasks, normalization_trace = normalize_tasks_with_trace(tasks)
                    removed = task_count_before_normalization - len(tasks)
                    metrics.duplicate_tasks_removed += removed
                    event("normalization", removed=removed, trace=normalization_trace, tasks=[asdict(t) for t in tasks])
                validate_tasks(tasks)
                ordered = topological_order(tasks)
                task_results = []
                completed: dict[str, TaskResult] = {}
                per_task_budget = max(256, cfg.max_context_tokens // max(1, len(tasks)))
                controller = ContextController(max_tokens=per_task_budget)
                overlap_tracker = OverlapTracker() if flags["O"] else None
                for task in ordered:
                    dependency_context = " ".join(completed[d].answer for d in task.depends_on if d in completed)
                    retrieval_query, task_query_anchors = _build_task_retrieval_query(
                        task,
                        query,
                        dependency_context,
                    )
                    r0 = time.perf_counter()
                    candidates, retrieval_fallback_reason = await _retrieve_task_candidates_async(
                        retrieval_query,
                        query,
                        all_chunks,
                        top_k=cfg.task_top_k,
                        min_score=cfg.retrieval_min_score,
                        task_domain=task.domain,
                        retriever=self._retrieve,
                    )
                    metrics.retrieval_latency_ms += int((time.perf_counter() - r0) * 1000)
                    metrics.retrieved_chunks += len(candidates)
                    if flags["O"]:
                        selected, dropped, selected_log = controller.select_for_task(
                            candidates,
                            task_terms=_task_relevance_terms(
                                task,
                                retrieval_query,
                                query,
                                retrieval_fallback_reason,
                            ),
                            max_tokens=per_task_budget,
                        )
                    else:
                        # O-off baseline retains only invariant dedup/cap guards.
                        selected, dropped = controller.select(candidates)
                        selected_log = []
                    metrics.selected_chunks += len(selected)
                    metrics.dropped_chunks += len(dropped)
                    context_tokens = estimate_context_tokens(selected)
                    metrics.context_chars += sum(len(c.text) for c in selected)
                    metrics.context_tokens_est += context_tokens
                    overlap = overlap_tracker.observe(task.task_id, selected) if overlap_tracker else {
                        "shared_evidence_ids": [], "reused_from_task_ids": {}, "reuse_count": 0
                    }
                    event(
                        "task_retrieval",
                        task_id=task.task_id,
                        task_query_version=TASK_QUERY_FORMULATION_VERSION,
                        task_query_anchors=task_query_anchors,
                        candidates=[c.chunk_id for c in candidates],
                        retrieval_fallback_reason=retrieval_fallback_reason,
                        selected=[c.chunk_id for c in selected],
                        dropped=dropped,
                        selected_evidence=selected_log,
                        o_enabled=flags["O"],
                        shared_evidence_ids=overlap["shared_evidence_ids"],
                        reused_from_task_ids=overlap["reused_from_task_ids"],
                        context_tokens=context_tokens,
                        total_context_tokens=metrics.context_tokens_est,
                        scoring_version=RETRIEVAL_SCORING_VERSION,
                        domain_ranking_version=DOMAIN_RANKING_VERSION,
                        retrieval=dict(retrieval_metadata),
                    )
                    g0 = time.perf_counter()
                    result = await execute_task(provider, task, selected, metrics)
                    metrics.generation_latency_ms += int((time.perf_counter() - g0) * 1000)
                    completed[task.task_id] = result
                    task_results.append(result)
                    event("task_completed", result=asdict(result))
                    if metrics.input_tokens + metrics.output_tokens > cfg.max_run_tokens:
                        event("run_budget_exceeded", total_tokens=metrics.input_tokens + metrics.output_tokens)
                        break
                if overlap_tracker:
                    event("overlap_summary", o_enabled=True, **overlap_tracker.summary())
                g0 = time.perf_counter()
                answer = await synthesize(provider, query, task_results, metrics)
                metrics.generation_latency_ms += int((time.perf_counter() - g0) * 1000)

            status = "COMPLETE" if task_results and all(r.status == "COMPLETE" for r in task_results) else "PARTIAL"
            if task_results and all(r.status == "NO_EVIDENCE" for r in task_results):
                status = "NO_EVIDENCE"
            event("run_finished", status=status)
            return finalize(status, answer, tasks, task_results)
        except Exception as exc:
            event("run_failed", error_type=type(exc).__name__, error=str(exc))
            return finalize("FAILED", f"Pipeline failed: {type(exc).__name__}: {exc}", [], [])

    @staticmethod
    def _flags(condition: str) -> dict[str, bool]:
        definition = CONDITION_DEFINITIONS.get(condition)
        if definition is None:
            raise ValueError(f"Unknown condition {condition}")
        return {flag: bool(definition[flag]) for flag in ("P", "N", "O")}

    async def _retrieve(
        self,
        query: str,
        chunks: list[SourceChunk],
        *,
        top_k: int,
        min_score: float,
        domain: str | None = None,
        task_domain: str | None = None,
    ) -> list[SourceChunk]:
        if self.retriever is None:
            result = retrieve(
                query,
                chunks,
                top_k=top_k,
                min_score=min_score,
                domain=domain,
                task_domain=task_domain,
            )
        else:
            result = _call_retriever(
                self.retriever,
                query,
                chunks,
                top_k=top_k,
                min_score=min_score,
                domain=domain,
                task_domain=task_domain,
            )
            if inspect.isawaitable(result):
                result = await result
        if not isinstance(result, list) or any(
            not isinstance(chunk, SourceChunk) for chunk in result
        ):
            raise TypeError("retriever must return a list of SourceChunk values")
        return result

    async def _retrieval_metadata(self) -> dict[str, Any]:
        metadata = dict(_RETRIEVAL_METADATA_DEFAULTS)
        if self.retriever is None:
            return metadata

        target = self.retrieval_owner
        method = getattr(target, "index_identity", None)
        if method is None:
            method = getattr(target, "metadata", None)
        if method is None:
            method = getattr(target, "retrieval_metadata", None)
        if method is None and not callable(target):
            method = getattr(target, "status", None)
        if method is None:
            metadata["retrieval_backend"] = "custom"
            metadata["readiness"] = "unknown"
            return metadata
        value = method() if callable(method) else method
        if inspect.isawaitable(value):
            value = await value
        if not isinstance(value, Mapping):
            raise TypeError("retrieval metadata must be an object")
        metadata["retrieval_backend"] = "custom"
        metadata["readiness"] = "unknown"
        for key in _RETRIEVAL_METADATA_FIELDS:
            candidate = value.get(key)
            if candidate is None:
                continue
            if not isinstance(candidate, _RETRIEVAL_METADATA_SCALAR_TYPES):
                continue
            metadata[key] = candidate
        return metadata


def _runtime_tasks(decomposition: object) -> list[Task]:
    """Adapt the decomposer's locked schema to the legacy execution contract."""

    raw_tasks = getattr(decomposition, "tasks", decomposition)
    if not isinstance(raw_tasks, list):
        raise TypeError("decomposition must provide a task list")

    tasks: list[Task] = []
    for item in raw_tasks:
        if isinstance(item, Task):
            tasks.append(item)
            continue
        model_dump = getattr(item, "model_dump", None)
        if not callable(model_dump):
            raise TypeError("decomposition task must use the canonical task schema")
        values = model_dump()
        tasks.append(
            Task(
                task_id=values["task_id"],
                goal=values["objective"],
                domain=values["domain"],
                depends_on=list(values["depends_on"]),
            )
        )
    return tasks


def _obligation_trace_records(decomposition: object) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for obligation in getattr(decomposition, "required_obligations", []):
        model_dump = getattr(obligation, "model_dump", None)
        if callable(model_dump):
            records.append(dict(model_dump()))
        elif hasattr(obligation, "__dataclass_fields__"):
            records.append(dict(asdict(obligation)))
    return records


def _task_obligation_coverage(decomposition: object) -> list[dict[str, object]]:
    return [
        {
            "task_id": getattr(task, "task_id", ""),
            "covers_obligations": list(
                getattr(task, "covers_obligations", [])
            ),
        }
        for task in getattr(decomposition, "tasks", [])
    ]


def _call_retriever(
    retriever: Any,
    query: str,
    chunks: list[SourceChunk],
    *,
    top_k: int,
    min_score: float,
    domain: str | None,
    task_domain: str | None,
) -> Any:
    """Call an injected retriever without changing the lexical fallback API.

    The canonical seam is ``query`` plus retrieval kwargs.  ``chunks`` is
    passed only when the injected callable declares it, allowing a local
    knowledge service to own the source registry while a lightweight test
    retriever can still use the pipeline's snapshot.
    """

    method = retriever if callable(retriever) else getattr(retriever, "asearch", None)
    if method is None:
        method = getattr(retriever, "search", None)
    if method is None:
        method = getattr(retriever, "retrieve", None)
    if not callable(method):
        raise TypeError("retriever must be callable or expose search/retrieve")

    values = {
        "chunks": chunks,
        "top_k": top_k,
        "min_score": min_score,
        "domain": domain,
        "task_domain": task_domain,
    }
    try:
        parameters = inspect.signature(method).parameters
    except (TypeError, ValueError):
        parameters = {}
    if any(parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in parameters.values()):
        kwargs = values
    else:
        kwargs = {
            name: value
            for name, value in values.items()
            if name in parameters
        }
    return method(query, **kwargs)


def _preferred_retriever(retriever: Any | None) -> Any | None:
    """Prefer the async KB seam while retaining the legacy sync object path."""

    if retriever is None:
        return retriever
    async_search = getattr(retriever, "asearch", None)
    if callable(async_search):
        return async_search
    return retriever


async def _retrieve_task_candidates_async(
    task_query: str,
    original_request: str,
    chunks: list[SourceChunk],
    *,
    top_k: int,
    min_score: float,
    task_domain: str | None = None,
    retriever: Any | None = None,
) -> tuple[list[SourceChunk], str | None]:
    """Apply the task/domain fallback policy to sync or async retrieval."""

    async def search(query: str) -> list[SourceChunk]:
        if retriever is None:
            result = retrieve(
                query,
                chunks,
                top_k=top_k,
                min_score=min_score,
                task_domain=task_domain,
            )
        else:
            result = _call_retriever(
                retriever,
                query,
                chunks,
                top_k=top_k,
                min_score=min_score,
                domain=None,
                task_domain=task_domain,
            )
            if inspect.isawaitable(result):
                result = await result
        if not isinstance(result, list) or any(
            not isinstance(chunk, SourceChunk) for chunk in result
        ):
            raise TypeError("retriever must return a list of SourceChunk values")
        return result

    candidates = await search(task_query)
    if candidates:
        return candidates, None

    if task_domain and task_domain.strip():
        domain_query = f"{task_domain.strip()} {task_query}".strip()
        domain_candidates = await search(domain_query)
        if domain_candidates:
            return domain_candidates, TASK_QUERY_DOMAIN_FALLBACK_REASON

    fallback = await search(original_request)
    if fallback:
        return fallback, TASK_QUERY_FALLBACK_REASON
    return [], None


def _retrieve_task_candidates(
    task_query: str,
    original_request: str,
    chunks: list[SourceChunk],
    *,
    top_k: int,
    min_score: float,
    task_domain: str | None = None,
    retriever: Callable[..., list[SourceChunk]] | None = None,
) -> tuple[list[SourceChunk], str | None]:
    """Keep task/domain anchors before using the broad request fallback."""

    search = retriever or retrieve
    candidates = search(
        task_query,
        chunks,
        top_k=top_k,
        min_score=min_score,
        task_domain=task_domain,
    )
    if candidates:
        return candidates, None

    if task_domain and task_domain.strip():
        domain_query = f"{task_domain.strip()} {task_query}".strip()
        domain_candidates = search(
            domain_query,
            chunks,
            top_k=top_k,
            min_score=min_score,
            task_domain=task_domain,
        )
        if domain_candidates:
            return domain_candidates, TASK_QUERY_DOMAIN_FALLBACK_REASON

    fallback = search(
        original_request,
        chunks,
        top_k=top_k,
        min_score=min_score,
        task_domain=task_domain,
    )
    if fallback:
        return fallback, TASK_QUERY_FALLBACK_REASON
    return [], None


def _retrieval_query_with_conversation_context(
    query: str, conversation_context: ConversationContext
) -> str:
    """Use history only as bounded query disambiguation, never as evidence."""

    if not conversation_context.text:
        return query
    return (
        "CURRENT USER REQUEST:\n"
        f"{query}\n\n"
        "RECENT CONVERSATION CONTEXT (reference only; not source evidence):\n"
        f"{conversation_context.text}"
    )


def _task_relevance_terms(
    task: Task,
    task_query: str,
    original_request: str,
    fallback_reason: str | None,
) -> set[str]:
    """Use the query that produced candidates as O-lite's relevance boundary."""

    relevance = terms(task.goal) | terms(task_query)
    if fallback_reason == TASK_QUERY_FALLBACK_REASON:
        relevance.update(terms(original_request))
    return relevance


def _build_task_retrieval_query(
    task: Task,
    original_request: str,
    dependency_context: str = "",
) -> tuple[str, list[str]]:
    """Keep request anchors while avoiding noisy model-added paraphrases.

    The request remains the authority for task-specific retrieval. When the
    generated objective shares lexical anchors with the request, query only
    those anchors plus explicit task evidence needs and completed dependency
    context. A task with no shared anchors keeps its generated objective so
    the existing bounded fallback can record the miss explicitly.
    """

    request_terms = terms(original_request)
    objective_terms = terms(task.goal)
    anchors = sorted(request_terms.intersection(objective_terms))
    query_parts = [" ".join(anchors) if anchors else task.goal]
    query_parts.extend(task.evidence_needs)
    if dependency_context:
        query_parts.append(dependency_context)
    return " ".join(part.strip() for part in query_parts if part and part.strip()), anchors
