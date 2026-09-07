from __future__ import annotations
import time
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from app.core.config import CONDITION_DEFINITIONS, RuntimeConfig
from app.core.graph import topological_order, validate_tasks
from app.core.telemetry import process_rss_mb, gpu_memory_mb
from app.core.types import SourceChunk, Task, TaskResult, RunMetrics
from app.providers.factory import get_provider
from app.research.context_controller import ContextController, OverlapTracker
from app.research.decomposer import decompose
from app.research.normalizer import normalize_tasks_with_trace
from app.research.planning_retrieval import PlanningRetriever
from app.research.worker import execute_task
from app.research.synthesizer import synthesize
from app.research.vanilla import answer_vanilla
from app.retrieval.text import retrieve, apply_token_budget, estimate_tokens, terms
from app.storage.source_store import SourceStore
from app.storage.run_store import RunStore

CONDITIONS = {"A", "B", "C", "C-P", "C-N", "C-O"}
TASK_QUERY_FORMULATION_VERSION = "task-query-v2-anchor-preserving"
TASK_QUERY_FALLBACK_REASON = "task_query_no_results_fallback_to_user_request"
TASK_QUERY_DOMAIN_FALLBACK_REASON = "task_query_no_results_fallback_to_task_domain"

class ResearchPipeline:
    def __init__(self, source_store: SourceStore, run_store: RunStore):
        self.source_store = source_store
        self.run_store = run_store
        self.planning = PlanningRetriever()

    async def run(self, query: str, condition: str = "A", provider_name: str | None = None) -> dict:
        condition = condition.upper()
        if condition not in CONDITIONS:
            raise ValueError(f"Unknown condition {condition}")
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
                "retrieval_min_score": cfg.retrieval_min_score,
            }
            run = {
                "run_id": run_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "condition": condition,
                "implementation_profile": cfg.implementation_profile,
                "provider": provider.name,
                "model": provider.model,
                "query": query,
                "status": status,
                "answer": answer,
                "source_snapshot_id": source_snapshot,
                "config_hash": cfg.config_hash(),
                "tasks": [asdict(t) for t in tasks],
                "task_results": [asdict(r) for r in task_results],
                "metrics": metrics.to_dict(),
                "events": events,
                "effective_config": effective,
            }
            self.run_store.save(run)
            return run

        event(
            "run_started",
            condition=condition,
            provider=provider.name,
            model=provider.model,
            implementation_profile=cfg.implementation_profile,
            source_snapshot_id=source_snapshot,
            config_hash=cfg.config_hash(),
            flags=flags,
        )
        all_chunks = self.source_store.chunks()
        try:
            if condition == "A":
                r0 = time.perf_counter()
                candidates = retrieve(query, all_chunks, top_k=cfg.task_top_k, min_score=cfg.retrieval_min_score)
                metrics.retrieval_latency_ms += int((time.perf_counter() - r0) * 1000)
                metrics.retrieved_chunks += len(candidates)
                selected, budget_dropped = apply_token_budget(candidates, cfg.max_context_tokens)
                metrics.selected_chunks += len(selected)
                metrics.dropped_chunks += len(budget_dropped)
                metrics.context_chars += sum(len(c.text) for c in selected)
                metrics.context_tokens_est += sum(estimate_tokens(c.text) for c in selected)
                event(
                    "vanilla_retrieval",
                    candidates=[c.chunk_id for c in candidates],
                    selected=[c.chunk_id for c in selected],
                    dropped=budget_dropped,
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
                    event("planning_retrieval", selected=[c.chunk_id for c in planning_hits])
                g0 = time.perf_counter()
                decomposition = await decompose(provider, query, planning_context, metrics)
                tasks = _runtime_tasks(decomposition)
                metrics.generation_latency_ms += int((time.perf_counter() - g0) * 1000)
                event("decomposition", tasks=[asdict(t) for t in tasks])
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
                controller = ContextController(max_chars=per_task_budget * 3)
                overlap_tracker = OverlapTracker() if flags["O"] else None
                for task in ordered:
                    dependency_context = " ".join(completed[d].answer for d in task.depends_on if d in completed)
                    retrieval_query, task_query_anchors = _build_task_retrieval_query(
                        task,
                        query,
                        dependency_context,
                    )
                    r0 = time.perf_counter()
                    candidates, retrieval_fallback_reason = _retrieve_task_candidates(
                        retrieval_query,
                        query,
                        all_chunks,
                        top_k=cfg.task_top_k,
                        min_score=cfg.retrieval_min_score,
                        task_domain=task.domain,
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
                        selected, dropped = ContextController(max_tokens=per_task_budget).select(candidates)
                        selected_log = []
                    metrics.selected_chunks += len(selected)
                    metrics.dropped_chunks += len(dropped)
                    context_tokens = sum(estimate_tokens(c.text) for c in selected)
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


def _retrieve_task_candidates(
    task_query: str,
    original_request: str,
    chunks: list[SourceChunk],
    *,
    top_k: int,
    min_score: float,
    task_domain: str | None = None,
) -> tuple[list[SourceChunk], str | None]:
    """Keep task/domain anchors before using the broad request fallback."""

    candidates = retrieve(task_query, chunks, top_k=top_k, min_score=min_score)
    if candidates:
        return candidates, None

    if task_domain and task_domain.strip():
        domain_query = f"{task_domain.strip()} {task_query}".strip()
        domain_candidates = retrieve(domain_query, chunks, top_k=top_k, min_score=min_score)
        if domain_candidates:
            return domain_candidates, TASK_QUERY_DOMAIN_FALLBACK_REASON

    fallback = retrieve(original_request, chunks, top_k=top_k, min_score=min_score)
    if fallback:
        return fallback, TASK_QUERY_FALLBACK_REASON
    return [], None


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
