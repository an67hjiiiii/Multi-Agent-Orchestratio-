from __future__ import annotations
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from app.core.graph import validate_tasks
from app.core.types import (
    ObligationConcernExtraction,
    RunMetrics,
    Task,
    TaskPlan,
)
from app.research.registry import REGISTRY, validate_domain


def _extract_json(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            raise ValueError("Planner did not return JSON")
        return json.loads(m.group(0))

async def decompose(provider, query: str, planning_context: str, metrics: RunMetrics) -> list[Task]:
    system = "TASK_DECOMPOSER. Return JSON only. Preserve atomic obligations and dependencies. Do not invent requirements."
    user = f"USER REQUEST:\n{query}\n\nPLANNING CONTEXT:\n{planning_context}\n\nSchema: {{\"tasks\":[{{\"id\":\"T1\",\"goal\":\"...\",\"domain\":\"security|database|api_architecture\",\"depends_on\":[],\"evidence_needs\":[]}}]}}"
    result = await provider.generate(system=system, user=user)
    metrics.add_usage(result.usage)
    obj = _extract_json(result.text)
    tasks = []
    for i, raw in enumerate(obj.get("tasks") or []):
        tasks.append(Task(
            task_id=str(raw.get("id") or f"T{i+1}"),
            goal=str(raw.get("goal") or query),
            domain=str(raw.get("domain") or "api_architecture"),
            depends_on=[str(x) for x in raw.get("depends_on") or []],
            evidence_needs=[str(x) for x in raw.get("evidence_needs") or []],
        ))
    return tasks or [Task(task_id="T1", goal=query)]


# Group A planning contracts.  The legacy ``decompose`` function above remains
# list[Task]-compatible for the existing execution pipeline.  These bounded
# helpers provide the structured Sprint 3 planning seam without moving plan
# verification, normalization, workers, dispatch, or execution into this file.
CANONICAL_TASK_DOMAINS = tuple(REGISTRY)
_DOMAIN_HINTS = {
    "security": (
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
        "đăng nhập",
        "phân quyền",
    ),
    "database": (
        "database",
        "db",
        "schema",
        "query",
        "sql",
        "index",
        "transaction",
        "consistency",
        "table",
        "dữ liệu",
        "truy vấn",
    ),
    "api_architecture": (
        "api",
        "endpoint",
        "rest",
        "service",
        "architecture",
        "integration",
        "contract",
        "response",
        "kiến trúc",
        "giao diện api",
    ),
}
TASK_PLAN_SCHEMA = (
    '{"tasks":[{"task_id":"T1","goal":"...",'
    f'"domain":"{"|".join(CANONICAL_TASK_DOMAINS)}",'
    '"depends_on":[],"evidence_needs":[]}]}'
)
# Stable public alias for callers that used the schema-oriented name.
TASK_PLAN_JSON_SCHEMA = TASK_PLAN_SCHEMA
PLANNER_SYSTEM_PROMPT = (
    "TASK_PLAN_BUILDER. Return exactly one JSON object matching the task-plan "
    "schema. Preserve explicit obligations and dependencies; do not add "
    "verification, repair, worker, dispatch, or execution fields."
)
_TASK_ROOT_FIELDS = frozenset({"tasks"})
_TASK_FIELDS = frozenset(
    {"task_id", "id", "goal", "domain", "depends_on", "evidence_needs"}
)


@dataclass(frozen=True)
class RequestUnderstanding:
    """Bounded request understanding used to seed planning and routing."""

    request: str
    normalized_request: str
    domains: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "request": self.request,
            "normalized_request": self.normalized_request,
            "domains": list(self.domains),
        }


@dataclass
class PlanningResult:
    """Outcome of one plan generation plus at most one bounded repair."""

    request: str
    plan: TaskPlan | None = None
    status: str = "FAILED"
    warnings: list[str] = field(default_factory=list)
    repair_attempted: bool = False

    @property
    def tasks(self) -> list[Task]:
        """Expose the plan tasks without making execution part of planning."""

        return list(self.plan.tasks) if self.plan is not None else []


# Compatibility name for clients that use the decomposition-result wording.
DecompositionResult = PlanningResult


def _non_empty_request(request: str) -> str:
    if not isinstance(request, str) or not request.strip():
        raise ValueError("request must be a non-empty string")
    return request.strip()


def _contains_hint(text: str, hint: str) -> bool:
    if " " in hint:
        return hint in text
    return re.search(rf"(?<![\w]){re.escape(hint)}(?![\w])", text) is not None


def detect_domains(request: str) -> list[str]:
    """Return canonical domains explicitly signalled by the current request."""

    text = _non_empty_request(request).casefold()
    return [
        domain
        for domain in CANONICAL_TASK_DOMAINS
        if any(_contains_hint(text, hint) for hint in _DOMAIN_HINTS[domain])
    ]


def understand_request(request: str) -> RequestUnderstanding:
    """Normalize the request and detect only domains named by its text."""

    normalized = " ".join(_non_empty_request(request).split())
    return RequestUnderstanding(
        request=request,
        normalized_request=normalized,
        domains=tuple(detect_domains(normalized)),
    )


def _format_requirements(
    extraction: ObligationConcernExtraction | None,
) -> tuple[str, str]:
    if extraction is None:
        return "none", "none"
    obligations = "\n".join(
        f"- {item.obligation_id}: {item.description} (required={item.required})"
        for item in extraction.obligations
    ) or "none"
    concerns = "\n".join(
        f"- {item.concern_id}: {item.description} (domain={item.domain})"
        for item in extraction.concerns
    ) or "none"
    return obligations, concerns


def build_task_plan_prompt(
    request: str,
    planning_context: str = "",
    extraction: ObligationConcernExtraction | None = None,
) -> str:
    """Build the bounded task-plan prompt from request-owned inputs."""

    understanding = understand_request(request)
    obligations, concerns = _format_requirements(extraction)
    return (
        "OUTPUT PROTOCOL:\n"
        "Return exactly one JSON object and no markdown or explanation.\n"
        f"Schema: {TASK_PLAN_SCHEMA}\n\n"
        "CURRENT REQUEST:\n"
        f"{understanding.normalized_request}\n\n"
        "REQUEST DOMAINS (routing hints only):\n"
        f"{', '.join(understanding.domains) or 'none'}\n\n"
        "EXPLICIT OBLIGATIONS:\n"
        f"{obligations}\n\n"
        "EXPLICIT CONCERNS:\n"
        f"{concerns}\n\n"
        "PLANNING EVIDENCE (guidance only; never a new requirement):\n"
        f"{planning_context.strip() or 'none'}\n\n"
        "RULES:\n"
        "- Keep obligations and concerns distinct from tasks.\n"
        "- Preserve request-stated dependency direction in depends_on.\n"
        "- Use only security, database, or api_architecture task domains.\n"
        "- Emit no plan-verification, repair, worker, dispatch, or execution fields.\n"
        "Return JSON only."
    )


def _decode_task_plan_payload(payload: Mapping[str, Any] | str) -> Mapping[str, Any]:
    if isinstance(payload, Mapping):
        return payload
    if not isinstance(payload, str) or not payload.strip():
        raise ValueError("task plan output must be a JSON object")
    text = payload.strip()
    try:
        decoded = json.loads(text)
    except json.JSONDecodeError:
        fenced = re.fullmatch(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
        if not fenced:
            raise ValueError("task plan output must be exactly one JSON object") from None
        try:
            decoded = json.loads(fenced.group(1))
        except json.JSONDecodeError:
            raise ValueError("task plan output must be exactly one JSON object") from None
    if not isinstance(decoded, Mapping):
        raise ValueError("task plan output must be a JSON object")
    return decoded


def _validate_task_item_fields(raw: Mapping[str, Any], index: int) -> None:
    unsupported = [str(key) for key in raw if key not in _TASK_FIELDS]
    if unsupported:
        raise ValueError(
            f"task {index} contains unsupported fields: "
            + ", ".join(sorted(unsupported))
        )


def _required_string(raw: Mapping[str, Any], key: str, index: int) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"task {index}.{key} must be a non-empty string")
    return value


def _string_list(raw: Mapping[str, Any], key: str, index: int) -> list[str]:
    if key not in raw:
        raise ValueError(f"task {index} must include {key} as a list")
    value = raw[key]
    if not isinstance(value, list):
        raise ValueError(f"task {index}.{key} must be a list")
    values: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"task {index}.{key} must contain non-empty strings")
        values.append(item)
    return values


def parse_task_plan_output(
    payload: Mapping[str, Any] | str,
    request: str = "",
    extraction: ObligationConcernExtraction | None = None,
) -> TaskPlan:
    """Parse a strict task-only envelope into the existing ``TaskPlan`` contract."""

    obj = _decode_task_plan_payload(payload)
    unsupported = [str(key) for key in obj if key not in _TASK_ROOT_FIELDS]
    if unsupported:
        raise ValueError(
            "task plan contains unsupported root fields: "
            + ", ".join(sorted(unsupported))
        )
    if "tasks" not in obj:
        raise ValueError("task plan must contain a tasks list")
    raw_tasks = obj["tasks"]
    if not isinstance(raw_tasks, list):
        raise ValueError("task plan tasks must be a list")
    if not raw_tasks:
        raise ValueError("task plan tasks must contain at least one task")

    tasks: list[Task] = []
    for index, raw in enumerate(raw_tasks):
        if not isinstance(raw, Mapping):
            raise ValueError(f"task {index} must be an object")
        _validate_task_item_fields(raw, index)
        if "id" in raw and "task_id" in raw:
            raise ValueError(f"task {index} must use only one task ID field")
        id_key = "task_id" if "task_id" in raw else "id"
        identifier = _required_string(raw, id_key, index)
        goal = _required_string(raw, "goal", index)
        domain = _required_string(raw, "domain", index)
        try:
            validate_domain(domain)
        except ValueError as exc:
            raise ValueError(f"task {index}.domain: {exc}") from exc
        tasks.append(
            Task(
                task_id=identifier,
                goal=goal,
                domain=domain,
                depends_on=_string_list(raw, "depends_on", index),
                evidence_needs=_string_list(raw, "evidence_needs", index),
            )
        )
    validate_tasks(tasks)
    return TaskPlan(
        request=request,
        obligations=list(extraction.obligations) if extraction else [],
        concerns=list(extraction.concerns) if extraction else [],
        tasks=tasks,
    )


parse_task_plan = parse_task_plan_output


def build_task_plan_repair_prompt(
    request: str,
    previous_output: str,
    error: str,
    planning_context: str = "",
    extraction: ObligationConcernExtraction | None = None,
) -> str:
    """Request one bounded correction without widening the planning scope."""

    base = build_task_plan_prompt(request, planning_context, extraction)
    bounded_output = previous_output[:4000]
    return (
        f"{base}\n\n"
        "PREVIOUS INVALID TASK PLAN:\n"
        f"{bounded_output}\n\n"
        "VALIDATION ERROR:\n"
        f"{error[:500]}\n\n"
        "Return one corrected JSON object only. Preserve all valid IDs and "
        "request-stated dependency direction."
    )


def _safe_warning(error: BaseException) -> str:
    message = str(error).strip() or type(error).__name__
    message = re.sub(
        r"(?i)(token|password|secret|api[_ -]?key)\s*[:=]\s*\S+",
        r"\1=<redacted>",
        message,
    )
    return f"{type(error).__name__}: {message[:300]}"


async def decompose_plan(
    provider: Any,
    request: str,
    planning_context: str = "",
    metrics: RunMetrics | None = None,
    *,
    extraction: ObligationConcernExtraction | None = None,
    max_repairs: int = 1,
) -> PlanningResult:
    """Build a TaskPlan with one bounded invalid-output repair at most."""

    if max_repairs not in (0, 1):
        raise ValueError("max_repairs must be 0 or 1")
    metrics = metrics or RunMetrics()
    try:
        understanding = understand_request(request)
    except ValueError as error:
        return PlanningResult(request=str(request), warnings=[_safe_warning(error)])

    prompt = build_task_plan_prompt(
        understanding.normalized_request, planning_context, extraction
    )
    try:
        result = await provider.generate(system=PLANNER_SYSTEM_PROMPT, user=prompt)
        metrics.add_usage(result.usage)
    except Exception as error:
        return PlanningResult(
            request=understanding.normalized_request,
            warnings=[_safe_warning(error)],
        )

    try:
        plan = parse_task_plan_output(
            result.text, understanding.normalized_request, extraction
        )
        return PlanningResult(
            request=understanding.normalized_request,
            plan=plan,
            status="COMPLETE",
        )
    except (TypeError, ValueError) as first_error:
        if max_repairs == 0:
            return PlanningResult(
                request=understanding.normalized_request,
                warnings=[_safe_warning(first_error)],
            )
        repair_prompt = build_task_plan_repair_prompt(
            understanding.normalized_request,
            str(getattr(result, "text", "")),
            str(first_error),
            planning_context,
            extraction,
        )
        try:
            repaired = await provider.generate(
                system=PLANNER_SYSTEM_PROMPT,
                user=repair_prompt,
            )
            metrics.add_usage(repaired.usage)
            plan = parse_task_plan_output(
                repaired.text, understanding.normalized_request, extraction
            )
        except Exception as second_error:
            return PlanningResult(
                request=understanding.normalized_request,
                warnings=[_safe_warning(first_error), _safe_warning(second_error)],
                repair_attempted=True,
            )
        return PlanningResult(
            request=understanding.normalized_request,
            plan=plan,
            status="COMPLETE",
            repair_attempted=True,
        )


# Descriptive alias for callers that use the planning rather than decomposition
# vocabulary.  It remains bounded by ``decompose_plan``'s single repair.
build_task_plan = decompose_plan
