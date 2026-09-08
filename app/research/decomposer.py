from __future__ import annotations

import inspect
import json
import re
from dataclasses import dataclass, field
from typing import Any

from app.core.types import RunMetrics
from app.retrieval.text import terms as lexical_terms


try:
    # The schema track is integrated separately; use its canonical types when
    # it is available while keeping this focused commit independently runnable.
    from app.research.task_schema import (
        CANONICAL_TASK_DOMAINS,
        DecompositionResult,
        RequiredObligation,
        TaskItem,
        TaskPlan,
    )
except ModuleNotFoundError as exc:
    if exc.name != "app.research.task_schema":
        raise

    CANONICAL_TASK_DOMAINS = frozenset(
        {"security", "database", "api_architecture"}
    )

    @dataclass
    class TaskItem:
        task_id: str
        title: str
        objective: str
        expected_output: str
        domain: str
        role_profile: str
        depends_on: list[str] = field(default_factory=list)
        covers_obligations: list[str] = field(default_factory=list)

    @dataclass
    class RequiredObligation:
        obligation_id: str
        canonical_kind: str | None
        source_anchor: str

    @dataclass
    class DecompositionResult:
        request: str
        tasks: list[TaskItem] = field(default_factory=list)
        planning_evidence_ids: list[str] = field(default_factory=list)
        status: str = "FAILED"
        warnings: list[str] = field(default_factory=list)
        required_obligations: list[RequiredObligation] = field(default_factory=list)
        covered_obligations: list[str] = field(default_factory=list)
        missing_obligations: list[str] = field(default_factory=list)
        repair_attempted: bool = False
        coverage_validation_reason: str | None = None

    @dataclass
    class TaskPlan:
        tasks: list[TaskItem] = field(default_factory=list)


_PLANNING_ID_PATTERN = re.compile(r"\[([A-Za-z0-9_.:/-]+)\]")
_ORDERED_OBLIGATIONS_PATTERN = re.compile(
    r"\b(?:first|before)\b.+\b(?:then|after|next|subsequently)\b",
    re.IGNORECASE | re.DOTALL,
)
_REPEATED_OBLIGATIONS_PATTERN = re.compile(
    r"\b(?:repeat|recheck|re-examine|reexamine|again)\b|"
    r"\b(?:shared evidence|using shared evidence)\b",
    re.IGNORECASE,
)
_SEPARATE_OBLIGATIONS_PATTERN = re.compile(
    r"\b(?:each|every)\b[^.!?]*\b(?:separate|separately)\b|"
    r"\bseparate\s+(?:each|every)\b",
    re.IGNORECASE,
)
_LIST_BODY_PATTERNS = (
    re.compile(
        r"\b(?:combine|include|cover|address)\s+(?P<body>[^.!?]+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:review|assess|analy[sz]e)\b[^.!?]*?\bfor\s+(?P<body>[^.!?]+)",
        re.IGNORECASE,
    ),
)
_LIST_SEPARATOR_PATTERN = re.compile(
    r"\s*,\s*(?:and\s+)?|\s+\band\b\s+",
    re.IGNORECASE,
)
_TRAILING_OBLIGATION_LABEL = re.compile(r"\s+obligations?\s*$", re.IGNORECASE)
# These are request-level domain hints, not worker roles. They make the
# planner boundary fail closed when a multi-domain request is reduced to
# planning categories for only one domain.
_CANONICAL_DOMAIN_HINTS = {
    "security": frozenset(
        {
            "security",
            "auth",
            "authentication",
            "authorization",
            "jwt",
            "token",
            "permission",
            "identity",
            "login",
            "session",
        }
    ),
    "database": frozenset(
        {
            "database",
            "db",
            "schema",
            "query",
            "index",
            "transaction",
            "consistency",
            "table",
        }
    ),
    "api_architecture": frozenset(
        {
            "api",
            "endpoint",
            "rest",
            "service",
            "sla",
        }
    ),
}
_DOMAIN_LABEL_HINTS = {
    "security": frozenset({"security"}),
    "database": frozenset({"database", "db"}),
    "api_architecture": frozenset({"api", "endpoint", "rest", "service", "sla"}),
}
# A domain label in the request is not always an independent obligation.  In
# particular, "API" and "endpoint" commonly provide context for security or
# data-access work.  Require an API task only when the request also names an
# API-contract concern, while keeping security/database anchors explicit.
_DOMAIN_OBLIGATION_HINTS = {
    "security": _CANONICAL_DOMAIN_HINTS["security"] - _DOMAIN_LABEL_HINTS["security"],
    "database": _CANONICAL_DOMAIN_HINTS["database"],
    "api_architecture": frozenset(
        {"contract", "design", "architecture", "validation", "error", "response", "sla"}
    ),
}
# qwen3:4b has emitted these presentation labels in real Ollama traces.  They
# are deterministic aliases, not new domains; unknown labels remain rejected.
_CANONICAL_DOMAIN_ALIASES = {
    "security": "security",
    "security and identity management": "security",
    "security identity management": "security",
    "database": "database",
    "database management": "database",
    "database system": "database",
    "database systems": "database",
    "api design": "api_architecture",
    "api architecture": "api_architecture",
}
_REQUIRED_TASK_FIELDS = (
    "task_id",
    "title",
    "objective",
    "expected_output",
    "domain",
    "role_profile",
)
_TASK_SCHEMA = (
    '{"tasks":[{"task_id":"T1","title":"short task title",'
    '"objective":"specific objective",'
    '"expected_output":"expected structured output",'
    '"domain":"declared domain",'
    '"role_profile":"declared role profile",'
    '"depends_on":[],"covers_obligations":["O1"]}]}'
)
PROMPT_VERSION = "p-lite-decomposer-v7"
STRUCTURED_OUTPUT_CONFIG_VERSION = "ollama-task-plan-schema-v3"
PLANNER_TEMPERATURE = 0.0
TASK_PLAN_JSON_SCHEMA = TaskPlan.model_json_schema()
_TASK_ITEM_OUTPUT_SCHEMA = TASK_PLAN_JSON_SCHEMA.get("$defs", {}).get("TaskItem")
if isinstance(_TASK_ITEM_OUTPUT_SCHEMA, dict):
    _required_output_fields = list(_TASK_ITEM_OUTPUT_SCHEMA.get("required", []))
    if "covers_obligations" not in _required_output_fields:
        _required_output_fields.append("covers_obligations")
    _TASK_ITEM_OUTPUT_SCHEMA["required"] = _required_output_fields
_SYSTEM_PROMPT = (
    "TASK_DECOMPOSER. Follow the structured task-decomposition protocol in the "
    "user message. Do not invent requirements."
)
_STATIC_PROMPT_PREFIX = (
    f"PROMPT VERSION: {PROMPT_VERSION}\n"
    "OUTPUT PROTOCOL:\n"
    "Return exactly one JSON object and no markdown or explanation.\n"
    f"Schema: {_TASK_SCHEMA}\n\n"
    "PLANNER RULES:\n"
    "The current request is the sole source of obligations. Planning evidence is "
    "non-binding guidance only; never let it add a category, domain, implementation "
    "detail, evidence need, or task that is not stated or directly implied by the "
    "request. Identify one task per explicit independent obligation before writing "
    "tasks; do not enumerate every category listed in a planning item. Add a "
    "dependency only when the request states order, causality, or that one task "
    "consumes another task's output. Repeat, recheck, and shared-evidence wording "
    "does not create a dependency by itself. Use only canonical domain IDs: "
    "security, database, or api_architecture. Preserve high-signal request terms "
    "in each title and objective instead of adding guessed specifics. For a "
    "request naming multiple domains, emit at least one task anchored to each "
    "named domain; distinct obligations in the same domain remain separate when "
    "each has its own request anchor. Do not enumerate planning categories as "
    "extra tasks when the request does not name them. Do not add N/O, "
    "execution, retrieval, or answer evidence. For explicitly ordered or dependent "
    "obligations, emit separate tasks with separate expected outputs and put the "
    "predecessor task ID in depends_on. Every task must include every schema field; "
    "use depends_on: [] when it has no predecessor. Every task must list the request-"
    "derived obligation IDs it covers in covers_obligations. Never emit blank "
    "placeholder tasks."
)


class _DecompositionOutputError(ValueError):
    """Raised when a model response cannot satisfy the P-lite contract."""


@dataclass
class _CoverageState:
    covered_ids: list[str]
    missing_ids: list[str]
    reason: str


class _CoverageValidationError(_DecompositionOutputError):
    def __init__(self, state: _CoverageState):
        super().__init__(state.reason)
        self.state = state


def _extract_planning_evidence_ids(planning_context: str) -> list[str]:
    """Preserve only evidence identifiers present in the bounded context."""

    return list(dict.fromkeys(_PLANNING_ID_PATTERN.findall(planning_context)))


def _canonical_obligation_kind(source_anchor: str) -> str | None:
    anchor_terms = lexical_terms(source_anchor)
    matches = [
        domain
        for domain, hints in _DOMAIN_OBLIGATION_HINTS.items()
        if anchor_terms & hints
    ]
    return matches[0] if len(matches) == 1 else None


def _derive_required_obligations(request: str) -> list[RequiredObligation]:
    """Extract a bounded explicit list while retaining exact request anchors.

    The request is the only source. If it does not contain a clear list clause,
    the complete request remains one traceable obligation rather than being
    expanded from domain templates or planning evidence.
    """

    body: str | None = None
    for pattern in _LIST_BODY_PATTERNS:
        match = pattern.search(request)
        if match:
            candidate = match.group("body").strip()
            if "," in candidate or re.search(r"\band\b", candidate, re.IGNORECASE):
                body = candidate
                break

    anchors: list[str] = []
    if body:
        for raw_anchor in _LIST_SEPARATOR_PATTERN.split(body):
            anchor = raw_anchor.strip(" \t\r\n,;:-")
            anchor = _TRAILING_OBLIGATION_LABEL.sub("", anchor).strip()
            if anchor:
                anchors.append(anchor)
    if len(anchors) < 2:
        anchors = [request.strip()]

    return [
        RequiredObligation(
            obligation_id=f"O{index}",
            canonical_kind=_canonical_obligation_kind(anchor),
            source_anchor=anchor,
        )
        for index, anchor in enumerate(anchors, start=1)
    ]


def _format_obligations(obligations: list[RequiredObligation]) -> str:
    return "\n".join(
        f"- {item.obligation_id} | canonical_kind={item.canonical_kind or 'unknown'} "
        f"| source_anchor={item.source_anchor}"
        for item in obligations
    )


def _extract_json(text: object) -> dict[str, Any]:
    if not isinstance(text, str) or not text.strip():
        raise _DecompositionOutputError("planner response was empty")

    cleaned = text.strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        if start < 0:
            raise _DecompositionOutputError("planner response did not contain a JSON object")
        try:
            parsed, _ = json.JSONDecoder().raw_decode(cleaned[start:])
        except json.JSONDecodeError as exc:
            raise _DecompositionOutputError("planner response contained invalid JSON") from exc

    if not isinstance(parsed, dict):
        raise _DecompositionOutputError("planner response must be a JSON object")
    return parsed


def _required_text(raw: dict[str, Any], field_name: str, task_index: int) -> str:
    value = raw.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise _DecompositionOutputError(
            f"task {task_index} field {field_name} must be a non-empty string"
        )
    return value.strip()


def _canonical_domain(value: str) -> str | None:
    """Map only observed presentation labels to the locked domain IDs."""

    normalized = re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()
    return _CANONICAL_DOMAIN_ALIASES.get(normalized)


def _parse_tasks(parsed: dict[str, Any]) -> list[TaskItem]:
    raw_tasks = parsed.get("tasks")
    if not isinstance(raw_tasks, list) or not raw_tasks:
        raise _DecompositionOutputError("planner response must contain a non-empty tasks list")

    tasks: list[TaskItem] = []
    for index, raw in enumerate(raw_tasks, start=1):
        if not isinstance(raw, dict):
            raise _DecompositionOutputError(f"task {index} must be a JSON object")

        values = {
            field_name: _required_text(raw, field_name, index)
            for field_name in _REQUIRED_TASK_FIELDS
        }
        raw_dependencies = raw.get("depends_on", [])
        if not isinstance(raw_dependencies, list):
            raise _DecompositionOutputError(f"task {index} depends_on must be a list")

        dependencies: list[str] = []
        for dependency in raw_dependencies:
            if not isinstance(dependency, str) or not dependency.strip():
                raise _DecompositionOutputError(
                    f"task {index} depends_on must contain non-empty strings"
                )
            dependencies.append(dependency.strip())

        raw_coverage = raw.get("covers_obligations", [])
        if not isinstance(raw_coverage, list):
            raise _DecompositionOutputError(
                f"task {index} covers_obligations must be a list"
            )
        coverage_ids: list[str] = []
        for obligation_id in raw_coverage:
            if not isinstance(obligation_id, str) or not obligation_id.strip():
                raise _DecompositionOutputError(
                    f"task {index} covers_obligations must contain non-empty strings"
                )
            normalized_id = obligation_id.strip()
            if normalized_id not in coverage_ids:
                coverage_ids.append(normalized_id)

        canonical_domain = _canonical_domain(values["domain"])
        if canonical_domain is None or canonical_domain not in CANONICAL_TASK_DOMAINS:
            raise _DecompositionOutputError(
                f"task {index} domain must be one of the canonical task domains"
            )
        values["domain"] = canonical_domain
        try:
            tasks.append(
                TaskItem(
                    **values,
                    depends_on=dependencies,
                    covers_obligations=coverage_ids,
                )
            )
        except (TypeError, ValueError) as exc:
            raise _DecompositionOutputError(
                f"task {index} did not satisfy the canonical task schema"
            ) from exc

    _validate_dependencies(tasks)
    return tasks


def _validate_dependencies(tasks: list[TaskItem]) -> None:
    task_ids = [task.task_id for task in tasks]
    if len(task_ids) != len(set(task_ids)):
        raise _DecompositionOutputError("task_id values must be unique")

    known_ids = set(task_ids)
    indegree = {task_id: 0 for task_id in task_ids}
    dependents: dict[str, list[str]] = {task_id: [] for task_id in task_ids}
    for task in tasks:
        if len(task.depends_on) != len(set(task.depends_on)):
            raise _DecompositionOutputError("task dependency list contains duplicate entries")
        for dependency in task.depends_on:
            if dependency not in known_ids:
                raise _DecompositionOutputError("task dependency references an unknown task ID")
            if dependency == task.task_id:
                raise _DecompositionOutputError("task dependency cannot reference its own task ID")
            dependents[dependency].append(task.task_id)
            indegree[task.task_id] += 1

    ready = [task_id for task_id in task_ids if indegree[task_id] == 0]
    visited = 0
    while ready:
        current = ready.pop(0)
        visited += 1
        for dependent in dependents[current]:
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                ready.append(dependent)
    if visited != len(task_ids):
        raise _DecompositionOutputError("task dependency graph contains a cycle")


def _validate_request_alignment(request: str, tasks: list[TaskItem]) -> None:
    """Keep multi-domain plans anchored to the obligations in the request.

    Planning guidance can describe several categories for one domain.  It must
    not turn those examples into tasks when the request names another domain or
    a narrower obligation.  The check is intentionally conservative: it only
    runs when at least two canonical domains are signalled by the request, and
    it never merges distinct tasks.
    """

    request_terms = lexical_terms(request)
    requested_domains = {
        domain
        for domain, hints in _DOMAIN_OBLIGATION_HINTS.items()
        if request_terms & hints
    }
    if len(requested_domains) < 2:
        if len(tasks) == 1:
            expected_domain = next(iter(requested_domains), None)
            if expected_domain is not None and tasks[0].domain != expected_domain:
                raise _DecompositionOutputError(
                    "single task domain must match the sole requested canonical domain"
                )
        return

    task_domains = {task.domain for task in tasks}
    missing_domains = sorted(requested_domains - task_domains)
    if missing_domains:
        raise _DecompositionOutputError(
            "planner tasks must preserve each named request obligation/domain; "
            "missing canonical request domains: " + ", ".join(missing_domains)
        )

    for domain in sorted(requested_domains):
        domain_tasks = [task for task in tasks if task.domain == domain]
        # A single canonical task is enough to represent a named domain even
        # when its wording paraphrases the request (for example, a security
        # task may omit one specific token/authentication synonym).  Anchor
        # checks remain strict for repeated tasks, where planning categories
        # can otherwise become unrequested extra work.
        if len(domain_tasks) == 1:
            continue

        request_anchors = request_terms & _DOMAIN_OBLIGATION_HINTS[domain]
        if not request_anchors:
            raise _DecompositionOutputError(
                "repeated domain tasks must retain concrete request anchors; "
                "planning categories alone do not justify extra tasks"
            )

        anchored_tasks = [
            task
            for task in domain_tasks
            if lexical_terms(f"{task.title} {task.objective}") & request_anchors
        ]
        if not anchored_tasks:
            raise _DecompositionOutputError(
                "planner tasks must preserve a concrete anchor for each named "
                "request obligation"
            )
        if len(domain_tasks) > 1 and len(anchored_tasks) != len(domain_tasks):
            raise _DecompositionOutputError(
                "repeated domain tasks must retain distinct request anchors; "
                "planning categories alone do not justify extra tasks"
            )


def _validate_explicit_coverage(
    request: str,
    tasks: list[TaskItem],
    required_obligations: list[RequiredObligation],
) -> _CoverageState:
    required_by_id = {
        obligation.obligation_id: obligation for obligation in required_obligations
    }
    covered: set[str] = set()
    invalid_reasons: list[str] = []
    requires_separate_tasks = bool(_SEPARATE_OBLIGATIONS_PATTERN.search(request))

    for task in tasks:
        coverage_ids = list(dict.fromkeys(task.covers_obligations))
        if not coverage_ids and len(required_obligations) == 1:
            only = required_obligations[0]
            task_text = f"{task.title} {task.objective} {task.expected_output}"
            domain_matches = (
                only.canonical_kind is None or task.domain == only.canonical_kind
            )
            if domain_matches and lexical_terms(task_text) & lexical_terms(
                only.source_anchor
            ):
                coverage_ids = [only.obligation_id]
                task.covers_obligations = coverage_ids

        if requires_separate_tasks and len(coverage_ids) > 1:
            invalid_reasons.append(
                f"task {task.task_id} combines obligations that the request requires separately"
            )
            continue

        task_text_terms = lexical_terms(
            f"{task.title} {task.objective} {task.expected_output}"
        )
        for obligation_id in coverage_ids:
            obligation = required_by_id.get(obligation_id)
            if obligation is None:
                invalid_reasons.append(
                    f"task {task.task_id} references unknown obligation {obligation_id}"
                )
                continue
            if not task_text_terms.intersection(lexical_terms(obligation.source_anchor)):
                invalid_reasons.append(
                    f"task {task.task_id} does not retain source anchor for {obligation_id}"
                )
                continue
            if (
                obligation.canonical_kind is not None
                and task.domain != obligation.canonical_kind
            ):
                invalid_reasons.append(
                    f"task {task.task_id} domain does not match {obligation_id}"
                )
                continue
            covered.add(obligation_id)

    covered_ids = [
        obligation.obligation_id
        for obligation in required_obligations
        if obligation.obligation_id in covered
    ]
    missing_ids = [
        obligation.obligation_id
        for obligation in required_obligations
        if obligation.obligation_id not in covered
    ]
    if invalid_reasons or missing_ids:
        reason_parts = invalid_reasons
        if missing_ids:
            reason_parts.append("missing required obligations: " + ", ".join(missing_ids))
        raise _CoverageValidationError(
            _CoverageState(covered_ids, missing_ids, "; ".join(reason_parts))
        )
    return _CoverageState(covered_ids, [], "complete obligation coverage")


def _validate_obligation_coverage(
    request: str,
    tasks: list[TaskItem],
    required_obligations: list[RequiredObligation],
) -> _CoverageState:
    """Validate explicit request coverage plus the existing dependency contract."""

    coverage = _validate_explicit_coverage(request, tasks, required_obligations)
    _validate_request_alignment(request, tasks)
    ordered = bool(_ORDERED_OBLIGATIONS_PATTERN.search(request))
    if ordered:
        if len(tasks) < 2:
            raise _DecompositionOutputError(
                "explicitly ordered obligations require separate tasks"
            )
        if not any(task.depends_on for task in tasks):
            raise _DecompositionOutputError(
                "explicitly ordered obligations require a dependency"
            )
        return coverage

    if _REPEATED_OBLIGATIONS_PATTERN.search(request) and any(
        task.depends_on for task in tasks
    ):
        raise _DecompositionOutputError(
            "repeated or shared-evidence obligations are independent unless "
            "the request states an order or dependency"
        )
    return coverage


def _supports_generation_keyword(provider: object, keyword: str) -> bool:
    try:
        parameters = inspect.signature(provider.generate).parameters.values()
    except (AttributeError, TypeError, ValueError):
        return False
    return any(
        parameter.name == keyword or parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in parameters
    )


async def _generate_structured(provider: object, system: str, user: str):
    kwargs: dict[str, object] = {"system": system, "user": user}
    if _supports_generation_keyword(provider, "think"):
        kwargs["think"] = False
    if _supports_generation_keyword(provider, "format"):
        kwargs["format"] = TASK_PLAN_JSON_SCHEMA
    if _supports_generation_keyword(provider, "temperature"):
        kwargs["temperature"] = PLANNER_TEMPERATURE
    return await provider.generate(**kwargs)


def _prompt(
    query: str,
    planning_context: str,
    required_obligations: list[RequiredObligation],
    retry_reason: str | None = None,
    previous_plan: str = "",
    coverage: _CoverageState | None = None,
) -> str:
    retry_note = ""
    if retry_reason:
        covered_ids = coverage.covered_ids if coverage else []
        missing_ids = coverage.missing_ids if coverage else [
            item.obligation_id for item in required_obligations
        ]
        missing_set = set(missing_ids)
        missing_obligations = [
            item for item in required_obligations if item.obligation_id in missing_set
        ]
        retry_note = (
            "\n\nPREVIOUS INVALID TASK PLAN:\n"
            f"{previous_plan}\n\n"
            "COVERAGE REPAIR:\n"
            f"Previous validation failure: {retry_reason}\n"
            f"Already covered obligation IDs: {', '.join(covered_ids) or 'none'}\n"
            "Missing obligations:\n"
            f"{_format_obligations(missing_obligations)}\n"
            "Return one corrected complete plan. Preserve every already-covered "
            "obligation and add coverage for every missing obligation. Do not replace "
            "one covered set with another. Return a corrected JSON object only."
        )
    return (
        f"{_STATIC_PROMPT_PREFIX}\n\n"
        "CURRENT REQUEST:\n"
        f"{query}\n\n"
        "PLANNING EVIDENCE (guidance only; not answer evidence):\n"
        f"{planning_context}\n\n"
        "REQUIRED OBLIGATIONS (derived only from the current request):\n"
        f"{_format_obligations(required_obligations)}"
        f"{retry_note}"
    )


def _safe_warning(exc: BaseException) -> str:
    if isinstance(exc, _DecompositionOutputError):
        return str(exc)
    return f"planner generation failed with {type(exc).__name__}"


def _failed_result(
    query: str,
    planning_evidence_ids: list[str],
    warning: str,
    *,
    required_obligations: list[RequiredObligation] | None = None,
    coverage: _CoverageState | None = None,
    repair_attempted: bool = False,
) -> DecompositionResult:
    required = required_obligations or []
    return DecompositionResult(
        request=query,
        tasks=[],
        planning_evidence_ids=planning_evidence_ids,
        status="FAILED",
        warnings=[warning],
        required_obligations=required,
        covered_obligations=list(coverage.covered_ids) if coverage else [],
        missing_obligations=(
            list(coverage.missing_ids)
            if coverage
            else [item.obligation_id for item in required]
        ),
        repair_attempted=repair_attempted,
        coverage_validation_reason=warning,
    )


async def decompose(
    provider,
    query: str,
    planning_context: str,
    metrics: RunMetrics,
) -> DecompositionResult:
    """Create a validated P-lite task plan from one bounded planning context.

    Only malformed structured output receives one repair attempt. Provider
    failures return a terminal failed result without exposing provider details.
    """

    if not isinstance(query, str) or not query.strip():
        safe_query = query if isinstance(query, str) else ""
        return _failed_result(safe_query, [], "request must be a non-empty string")
    if not isinstance(planning_context, str):
        return _failed_result(query, [], "planning context must be a string")

    request = query
    planning_evidence_ids = _extract_planning_evidence_ids(planning_context)
    required_obligations = _derive_required_obligations(request)
    system = _SYSTEM_PROMPT
    retry_reason: str | None = None
    previous_plan = ""
    coverage = _CoverageState(
        [],
        [item.obligation_id for item in required_obligations],
        "coverage not validated",
    )

    for attempt in range(2):
        try:
            result = await _generate_structured(
                provider,
                system,
                _prompt(
                    request,
                    planning_context,
                    required_obligations,
                    retry_reason,
                    previous_plan,
                    coverage,
                ),
            )
            metrics.add_usage(result.usage)
            previous_plan = result.text if isinstance(result.text, str) else ""
            tasks = _parse_tasks(_extract_json(result.text))
            coverage = _validate_obligation_coverage(
                request,
                tasks,
                required_obligations,
            )
            return DecompositionResult(
                request=request,
                tasks=tasks,
                planning_evidence_ids=planning_evidence_ids,
                status="COMPLETE",
                warnings=[],
                required_obligations=required_obligations,
                covered_obligations=coverage.covered_ids,
                missing_obligations=[],
                repair_attempted=attempt > 0,
                coverage_validation_reason=coverage.reason,
            )
        except _CoverageValidationError as exc:
            coverage = exc.state
            retry_reason = _safe_warning(exc)
            if attempt == 1:
                return _failed_result(
                    request,
                    planning_evidence_ids,
                    retry_reason,
                    required_obligations=required_obligations,
                    coverage=coverage,
                    repair_attempted=True,
                )
        except _DecompositionOutputError as exc:
            retry_reason = _safe_warning(exc)
            if attempt == 1:
                return _failed_result(
                    request,
                    planning_evidence_ids,
                    retry_reason,
                    required_obligations=required_obligations,
                    coverage=coverage,
                    repair_attempted=True,
                )
        except Exception as exc:
            return _failed_result(
                request,
                planning_evidence_ids,
                _safe_warning(exc),
                required_obligations=required_obligations,
                coverage=coverage,
                repair_attempted=bool(retry_reason),
            )

    return _failed_result(
        request,
        planning_evidence_ids,
        "planner output could not be validated",
        required_obligations=required_obligations,
        coverage=coverage,
        repair_attempted=True,
    )


__all__ = ["DecompositionResult", "TaskItem", "decompose"]
