"""Sprint 3 P-lite: planning retrieval followed by task inspection.

The slice stops before task execution, answer-domain retrieval, normalization,
and overlap-aware context allocation.
"""

from __future__ import annotations

import inspect
import math
import time
from dataclasses import asdict, dataclass, field, is_dataclass
from types import SimpleNamespace
from typing import Any, Callable

from app.core.graph import validate_tasks as validate_graph
from app.core.types import RunMetrics, Usage
from app.providers.factory import get_provider
from app.research.decomposer import decompose as default_decompose
from app.research.planning_retrieval import PlanningRetriever
from app.retrieval.text import estimate_tokens, normalize_text

try:
    from app.research import task_schema
except ImportError:
    task_schema = None


@dataclass(frozen=True)
class PlanningRetrievalResult:
    """The planning evidence actually exposed to the decomposer."""

    request: str
    item_ids: list[str]
    scores: list[float] | None
    context: str


@dataclass
class PLiteInspectionResult:
    """Locked decomposition fields plus bounded planning and telemetry data."""

    request: str
    tasks: list[Any]
    planning_evidence_ids: list[str]
    status: str
    warnings: list[str]
    planning: PlanningRetrievalResult
    planning_context: str
    latency_ms: int
    llm_calls: int
    metrics: RunMetrics = field(default_factory=RunMetrics, repr=False, compare=False)

    @property
    def planning_result(self) -> PlanningRetrievalResult:
        return self.planning

    def to_dict(self) -> dict[str, Any]:
        return {
            "request": self.request,
            "tasks": [_serialize_task(task) for task in self.tasks],
            "planning_evidence_ids": list(self.planning_evidence_ids),
            "status": self.status,
            "warnings": list(self.warnings),
            "planning": asdict(self.planning),
            "planning_context": self.planning_context,
            "latency_ms": self.latency_ms,
            "llm_calls": self.llm_calls,
            "metrics": self.metrics.to_dict(),
        }


PLiteResult = PLiteInspectionResult


@dataclass(frozen=True)
class _PlanningItem:
    item_id: str
    domain: str
    title: str
    content: str
    provenance: str
    score: float | None


class PLitePipeline:
    """Compose planning retrieval, bounded context, decomposition, and checks."""

    def __init__(
        self,
        planning_retriever: Any | None = None,
        decomposer: Callable[..., Any] | Any | None = None,
        *,
        planning_top_k: int = 3,
        max_items: int = 3,
        max_context_tokens: int = 1_200,
        retry_limit: int = 1,
    ) -> None:
        self.planning_retriever = (
            planning_retriever if planning_retriever is not None else PlanningRetriever()
        )
        self.decomposer = decomposer if decomposer is not None else default_decompose
        self.planning_top_k = _positive_int(planning_top_k, "planning_top_k")
        self.max_items = _positive_int(max_items, "max_items")
        self.max_context_tokens = _positive_int(max_context_tokens, "max_context_tokens")
        invalid_retry = (
            isinstance(retry_limit, bool)
            or not isinstance(retry_limit, int)
            or retry_limit not in {0, 1}
        )
        if invalid_retry:
            raise ValueError("retry_limit must be 0 or 1 for P-lite")
        self.retry_limit = retry_limit

    async def run(
        self,
        request: str,
        provider: Any,
        metrics: RunMetrics | None = None,
    ) -> PLiteInspectionResult:
        request = _required_request(request)
        provider = _local_provider(provider)
        metrics = metrics if metrics is not None else RunMetrics()
        started = time.perf_counter()
        initial_calls = metrics.llm_calls
        warnings: list[str] = []

        try:
            planning, retrieval_warnings = await self._retrieve_planning(request, metrics)
            warnings.extend(retrieval_warnings)
        except Exception as exc:
            warnings.append(f"planning retrieval failed: {type(exc).__name__}")
            return self._result(
                request, [], _empty_planning(request), "FAILED", warnings,
                metrics, initial_calls, started,
            )

        decomposition_warnings: list[str] = []
        # The built-in decomposer owns its one structured repair attempt. A
        # second wrapper retry would multiply local model calls and exceed the
        # P-lite contract; injected decomposers retain the explicit retry cap.
        attempts = 1 if self.decomposer is default_decompose else self.retry_limit + 1
        for attempt in range(attempts):
            try:
                calls_before = metrics.llm_calls
                generation_started = time.perf_counter()
                try:
                    decomposer = getattr(self.decomposer, "decompose", self.decomposer)
                    raw = decomposer(provider, request, planning.context, metrics)
                    raw = await _maybe_await(raw)
                finally:
                    metrics.generation_latency_ms += _elapsed_ms(generation_started)

                _record_decomposer_call(raw, metrics, calls_before)
                tasks, status, decomposition_warnings = _unpack_decomposition(raw)
                _validate_decomposition(tasks)
                if attempt:
                    warnings.append("structured decomposition retry used")
                return self._result(
                    request, tasks, planning, status,
                    [*warnings, *decomposition_warnings],
                    metrics, initial_calls, started,
                )
            except (TypeError, ValueError) as exc:
                if attempt < attempts - 1:
                    continue
                warnings.append(f"decomposition validation failed: {type(exc).__name__}")
                return self._result(
                    request, [], planning, "FAILED",
                    [*warnings, *decomposition_warnings],
                    metrics, initial_calls, started,
                )
            except Exception as exc:
                # Detailed provider errors stay in the adapter boundary.
                warnings.append(f"decomposer failed: {type(exc).__name__}")
                return self._result(
                    request, [], planning, "FAILED", warnings,
                    metrics, initial_calls, started,
                )

        raise RuntimeError("unreachable P-lite retry state")

    async def _retrieve_planning(
        self,
        request: str,
        metrics: RunMetrics,
    ) -> tuple[PlanningRetrievalResult, list[str]]:
        retrieval_started = time.perf_counter()
        try:
            method = getattr(self.planning_retriever, "search", None)
            if method is None:
                method = self.planning_retriever.retrieve
            raw = await _maybe_await(method(request, top_k=self.planning_top_k))
        finally:
            metrics.retrieval_latency_ms += _elapsed_ms(retrieval_started)

        items, supplied_context, supplied_ids, supplied_scores = _unpack_retrieval(raw)
        candidates: list[_PlanningItem] = []
        seen_ids: set[str] = set()
        seen_content: set[str] = set()
        for index, value in enumerate(items[: self.planning_top_k]):
            item = _coerce_item(value, index)
            if item.item_id in seen_ids or item.content.casefold() in seen_content:
                continue
            seen_ids.add(item.item_id)
            if item.content:
                seen_content.add(item.content.casefold())
            candidates.append(item)

        warnings: list[str] = []
        if len(items) > self.planning_top_k:
            warnings.append(f"planning retrieval capped at {self.planning_top_k} items")
        if candidates:
            context, selected, was_capped = _bound_items(
                candidates, self.max_items, self.max_context_tokens
            )
            if len(candidates) > self.max_items:
                warnings.append(f"planning context capped at {self.max_items} items")
            if was_capped:
                warnings.append(
                    f"planning context bounded at {self.max_context_tokens} tokens"
                )
            if not context:
                warnings.append("planning context is empty")
            return (
                PlanningRetrievalResult(
                    request=request,
                    item_ids=[item.item_id for item in selected],
                    scores=_scores(selected),
                    context=context,
                ),
                warnings,
            )

        context, was_capped = _bound_text(supplied_context, self.max_context_tokens)
        if was_capped:
            warnings.append(
                f"planning context bounded at {self.max_context_tokens} tokens"
            )
        item_ids = list(dict.fromkeys(_text(item_id, "") for item_id in supplied_ids))
        item_ids = [item_id for item_id in item_ids if item_id][: self.max_items]
        if not context:
            warnings.append("planning context is empty")
        return (
            PlanningRetrievalResult(
                request=request,
                item_ids=item_ids,
                scores=_bounded_scores(supplied_scores, len(item_ids)),
                context=context,
            ),
            warnings,
        )

    @staticmethod
    def _result(
        request: str,
        tasks: list[Any],
        planning: PlanningRetrievalResult,
        status: str,
        warnings: list[str],
        metrics: RunMetrics,
        initial_calls: int,
        started: float,
    ) -> PLiteInspectionResult:
        status = status.strip().upper() if isinstance(status, str) else "FAILED"
        if status not in {"COMPLETE", "PARTIAL", "NO_EVIDENCE", "FAILED"}:
            status = "PARTIAL"
            warnings.append("invalid decomposition status")
        latency_ms = _elapsed_ms(started)
        metrics.latency_ms = latency_ms
        return PLiteInspectionResult(
            request=request,
            tasks=tasks,
            planning_evidence_ids=list(planning.item_ids),
            status=status,
            warnings=list(dict.fromkeys(warnings)),
            planning=planning,
            planning_context=planning.context,
            latency_ms=latency_ms,
            llm_calls=max(0, metrics.llm_calls - initial_calls),
            metrics=metrics,
        )


async def run_p_lite(
    request: str,
    provider: Any,
    metrics: RunMetrics | None = None,
    **pipeline_options: Any,
) -> PLiteInspectionResult:
    return await PLitePipeline(**pipeline_options).run(request, provider, metrics)


def _positive_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _required_request(request: object) -> str:
    if not isinstance(request, str) or not request.strip():
        raise ValueError("request must be a non-empty string")
    return request.strip()


def _local_provider(provider: Any) -> Any:
    if isinstance(provider, str):
        provider = get_provider(provider)
    if provider is None or not callable(getattr(provider, "generate", None)):
        raise ValueError("P-lite requires the local provider adapter")
    name = str(getattr(provider, "name", "")).strip().casefold()
    if name and name not in {"ollama", "local", "fake", "base"}:
        raise ValueError("Only fake and local Ollama providers are allowed")
    return provider


async def _maybe_await(value: Any) -> Any:
    return await value if inspect.isawaitable(value) else value


def _elapsed_ms(started: float) -> int:
    return max(0, int((time.perf_counter() - started) * 1000))


def _value(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default) if value is not None else default


def _unpack_retrieval(value: Any) -> tuple[list[Any], str, list[Any], Any]:
    if value is None or isinstance(value, (list, tuple)):
        return (list(value) if value is not None else []), "", [], None
    items = (
        _value(value, "items")
        or _value(value, "knowledge_items")
        or _value(value, "results")
        or []
    )
    if isinstance(items, (str, bytes)):
        items = []
    return (
        list(items),
        str(_value(value, "context", "") or ""),
        list(_value(value, "item_ids", []) or []),
        _value(value, "scores"),
    )


def _coerce_item(value: Any, index: int) -> _PlanningItem:
    item_id = _text(
        _value(value, "id") or _value(value, "item_id") or _value(value, "chunk_id"),
        f"planning_{index + 1}",
    )
    domain = _text(_value(value, "domain"), "planning")
    title = _text(_value(value, "title") or _value(value, "source_name") or item_id, item_id)
    content = _text(_value(value, "content") or _value(value, "text"), "")
    provenance = _text(
        _value(value, "provenance")
        or _value(value, "source_name")
        or _value(value, "source_id"),
        "planning",
    )
    raw_score = _value(value, "score")
    try:
        score = float(raw_score) if raw_score is not None else None
        if score is not None and not math.isfinite(score):
            score = None
    except (TypeError, ValueError):
        score = None
    return _PlanningItem(item_id, domain, title, content, provenance, score)


def _text(value: Any, default: str) -> str:
    if value is None:
        return default
    return normalize_text(str(value)) or default


def _bound_items(
    items: list[_PlanningItem],
    max_items: int,
    max_context_tokens: int,
) -> tuple[str, list[_PlanningItem], bool]:
    selected: list[_PlanningItem] = []
    blocks: list[str] = []
    used_tokens = 0
    was_capped = len(items) > max_items
    for item in items[:max_items]:
        block = "\n".join(
            (
                f"[{item.item_id}]",
                f"Title: {item.title}",
                f"Domain: {item.domain}",
                f"Content: {item.content}",
                f"Provenance: {item.provenance}",
            )
        )
        separator = "\n\n" if blocks else ""
        remaining = max_context_tokens - used_tokens
        if remaining <= 0:
            was_capped = True
            break
        if estimate_tokens(separator + block) > remaining:
            if selected:
                was_capped = True
                break
            block = _truncate(block, remaining)
            if not block:
                was_capped = True
                break
            separator = ""
            was_capped = True
        selected.append(item)
        blocks.append(block)
        used_tokens += estimate_tokens(separator + block)
    return "\n\n".join(blocks), selected, was_capped


def _bound_text(value: str, max_context_tokens: int) -> tuple[str, bool]:
    clean = _text(value, "")
    if estimate_tokens(clean) <= max_context_tokens:
        return clean, False
    return _truncate(clean, max_context_tokens), True


def _truncate(value: str, max_tokens: int) -> str:
    excerpt = _text(value, "")[: max_tokens * 3]
    while excerpt and estimate_tokens(excerpt) > max_tokens:
        excerpt = excerpt[:-1]
    return excerpt


def _scores(items: list[_PlanningItem]) -> list[float] | None:
    if not items or not any(item.score is not None for item in items):
        return None
    return [item.score if item.score is not None else 0.0 for item in items]


def _bounded_scores(values: Any, count: int) -> list[float] | None:
    if not isinstance(values, (list, tuple)):
        return None
    scores: list[float] = []
    for value in list(values)[:count]:
        try:
            score = float(value)
        except (TypeError, ValueError):
            score = 0.0
        scores.append(score if math.isfinite(score) else 0.0)
    while len(scores) < count:
        scores.append(0.0)
    return scores or None


def _empty_planning(request: str) -> PlanningRetrievalResult:
    return PlanningRetrievalResult(request=request, item_ids=[], scores=None, context="")


def _unpack_decomposition(value: Any) -> tuple[list[Any], str, list[str]]:
    if isinstance(value, (list, tuple)):
        return list(value), "COMPLETE", []
    tasks = _value(value, "tasks")
    if tasks is None or isinstance(tasks, (str, bytes)) or not isinstance(tasks, (list, tuple)):
        raise ValueError("decomposer result must contain a task list")
    status = str(_value(value, "status", "COMPLETE") or "COMPLETE").strip().upper()
    warnings = _warnings(_value(value, "warnings", []))
    if status not in {"COMPLETE", "PARTIAL", "NO_EVIDENCE", "FAILED"}:
        status = "PARTIAL"
        warnings.append("invalid decomposition status")
    return list(tasks), status, warnings


def _validate_decomposition(tasks: list[Any]) -> None:
    if not tasks:
        raise ValueError("decomposer returned no tasks")

    validator = None
    if task_schema:
        for name in ("validate_tasks", "validate_task_items", "validate_decomposition"):
            validator = getattr(task_schema, name, None)
            if validator:
                validator(tasks)
                return

    adapted = []
    for index, task in enumerate(tasks, start=1):
        task_id = _value(task, "task_id") or _value(task, "id")
        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError(f"task {index} requires task_id")
        contract_fields = ("title", "objective", "expected_output", "domain", "role_profile")
        contract_present = any(
            _field_present(task, name)
            for name in ("title", "expected_output", "role_profile")
        )
        if contract_present:
            for name in contract_fields:
                value = _value(task, name)
                if not isinstance(value, str) or (name != "expected_output" and not value.strip()):
                    raise ValueError(f"task {task_id} has invalid {name}")
            if not _field_present(task, "depends_on"):
                raise ValueError(f"task {task_id} requires depends_on")
        elif not any(_value(task, name) for name in ("title", "objective", "goal")):
            raise ValueError(f"task {task_id} requires a title or objective")
        dependencies = _value(task, "depends_on", [])
        if not isinstance(dependencies, (list, tuple)):
            raise TypeError(f"task {task_id} depends_on must be a list")
        adapted.append(SimpleNamespace(task_id=task_id.strip(), depends_on=list(dependencies)))
    validate_graph(adapted)


def _field_present(value: Any, name: str) -> bool:
    return name in value if isinstance(value, dict) else hasattr(value, name)


def _warnings(value: Any) -> list[str]:
    values = value if isinstance(value, (list, tuple)) else [value]
    return list(dict.fromkeys(str(item).strip() for item in values if str(item).strip()))


def _record_decomposer_call(raw: Any, metrics: RunMetrics, before: int) -> None:
    if metrics.llm_calls != before:
        return
    usage = _value(raw, "usage")
    metrics.add_usage(
        Usage(
            _non_negative_int(_value(usage, "input_tokens")),
            _non_negative_int(_value(usage, "output_tokens")),
        )
    )


def _non_negative_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _serialize_task(task: Any) -> Any:
    if isinstance(task, dict):
        return dict(task)
    if is_dataclass(task):
        return asdict(task)
    model_dump = getattr(task, "model_dump", None)
    if callable(model_dump):
        return model_dump()
    return task
