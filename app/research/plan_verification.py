"""Verification boundary for request-derived task plans.

This module deliberately stays at the planning boundary.  It does not run a
worker, normalize tasks, or select evidence.  Graph/domain checks are delegated
to :func:`app.core.graph.validate_tasks` so this boundary cannot drift from the
existing task-validator contract.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import re
from dataclasses import dataclass, field, replace
from typing import Literal

from app.core.graph import validate_tasks
from app.core.types import TaskPlan
from app.research.registry import validate_domain
from app.research.decomposer import detect_domains
from app.retrieval.text import terms


GENERAL_CONCERN_DOMAIN = "general"
_GENERAL_CONCERN_PREFIX = "general concern about "
RepairAction = Literal["ACCEPT", "REPAIR", "REJECT"]

# These words describe the act of reviewing rather than the requested subject.
# They must not make an otherwise unrelated task appear to cover an obligation.
_LOW_SIGNAL_TERMS = frozenset(
    {
        "review",
        "reviews",
        "reviewing",
        "check",
        "checks",
        "checking",
        "verify",
        "verifies",
        "verifying",
        "assess",
        "assesses",
        "assessing",
        "analyze",
        "analyzes",
        "analyzing",
        "analysis",
        "request",
        "requirement",
        "requirements",
        "concern",
        "concerns",
        "task",
        "tasks",
    }
)


@dataclass(frozen=True)
class PlanVerification:
    """The complete, deterministic result of one plan verification pass."""

    valid: bool
    errors: tuple[str, ...] = ()
    covered_obligations: tuple[str, ...] = ()
    missing_required_obligations: tuple[str, ...] = ()
    uncovered_optional_obligations: tuple[str, ...] = ()
    covered_concerns: tuple[str, ...] = ()
    missing_concerns: tuple[str, ...] = ()
    misrouted_concerns: tuple[str, ...] = ()
    task_coverage: dict[str, dict[str, list[str]]] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        """Compatibility-friendly alias for callers that use an ``ok`` gate."""

        return self.valid


@dataclass(frozen=True)
class RepairDecision:
    """Whether the bounded planner repair step may be attempted."""

    action: RepairAction
    reasons: tuple[str, ...] = ()

    @property
    def should_repair(self) -> bool:
        return self.action == "REPAIR"


class TaskPlanValidationError(ValueError):
    """Raised by the strict validation helper with its structured report."""

    def __init__(self, report: PlanVerification):
        self.report = report
        super().__init__("; ".join(report.errors) or "TaskPlan is invalid")


def verify_task_plan(
    plan: TaskPlan,
    *,
    coverage: Mapping[str, Iterable[str]] | None = None,
) -> PlanVerification:
    """Verify one plan without mutating it or invoking a repair.

    ``coverage`` is an optional integration seam for a planner that emits
    explicit task-to-obligation IDs.  Current ``Task`` objects do not carry
    that field, so the default is conservative lexical retention of each
    obligation/concern description in the task goal.  Objects from a later
    schema that expose ``covers_obligations`` are accepted as well.
    """

    errors: list[str] = []
    covered_obligations: list[str] = []
    missing_required: list[str] = []
    uncovered_optional: list[str] = []
    covered_concerns: list[str] = []
    missing_concerns: list[str] = []
    misrouted_concerns: list[str] = []
    task_coverage: dict[str, dict[str, list[str]]] = {}

    if not isinstance(plan, TaskPlan):
        return PlanVerification(False, ("plan must be a TaskPlan",))

    errors.extend(_validate_plan_shape(plan))
    if not errors:
        try:
            # Reuse the established duplicate-ID, dependency, cycle, and
            # routable-task-domain rules rather than maintaining a second copy.
            validate_tasks(plan.tasks)
        except (AttributeError, TypeError, ValueError) as exc:
            errors.append(str(exc))

    if errors:
        return PlanVerification(False, tuple(dict.fromkeys(errors)))

    task_ids = {str(task.task_id) for task in plan.tasks}
    explicit_coverage, coverage_errors = _normalize_coverage(coverage, task_ids)
    errors.extend(coverage_errors)

    obligation_ids = {item.obligation_id for item in plan.obligations}
    for task in plan.tasks:
        task_coverage[task.task_id] = {"obligation_ids": [], "concern_ids": []}
        task_text = _task_text(task)
        claimed = explicit_coverage.get(task.task_id, []) if coverage is not None else None
        if coverage is None:
            raw_claims = getattr(task, "covers_obligations", None)
            claimed = _string_ids(raw_claims) if isinstance(raw_claims, list) else None

        if claimed is not None:
            for obligation_id in claimed:
                if obligation_id not in obligation_ids:
                    errors.append(
                        f"task {task.task_id} references unknown obligation {obligation_id}"
                    )
                    continue
                obligation = next(
                    item
                    for item in plan.obligations
                    if item.obligation_id == obligation_id
                )
                if not _retains_text(task_text, _source_text(obligation)):
                    errors.append(
                        f"task {task.task_id} does not retain obligation {obligation_id}"
                    )
                    continue
                domains = detect_domains(obligation.description)
                if len(domains) == 1 and task.domain != domains[0]:
                    errors.append(f"task {task.task_id} misroutes obligation {obligation_id}: expected {domains[0]}")
                    continue
                task_coverage[task.task_id]["obligation_ids"].append(obligation_id)
                if obligation_id not in covered_obligations:
                    covered_obligations.append(obligation_id)
        else:
            for obligation in plan.obligations:
                if _retains_text(task_text, _source_text(obligation)):
                    domains = detect_domains(obligation.description)
                    if len(domains) == 1 and task.domain != domains[0]:
                        continue
                    task_coverage[task.task_id]["obligation_ids"].append(obligation.obligation_id)
                    if obligation.obligation_id not in covered_obligations:
                        covered_obligations.append(obligation.obligation_id)

    for obligation in plan.obligations:
        if obligation.obligation_id in covered_obligations:
            continue
        if obligation.required:
            missing_required.append(obligation.obligation_id)
        else:
            uncovered_optional.append(obligation.obligation_id)

    for concern in plan.concerns:
        concern_text = _concern_text_for_coverage(concern)
        retaining_tasks = [
            task
            for task in plan.tasks
            if task.covers_concerns is None or concern.concern_id in task.covers_concerns
            if _retains_text(_task_text(task), concern_text)
        ]
        if not retaining_tasks:
            missing_concerns.append(concern.concern_id)
            continue
        if concern.domain != GENERAL_CONCERN_DOMAIN and not any(
            task.domain == concern.domain for task in retaining_tasks
        ):
            misrouted_concerns.append(concern.concern_id)
            continue
        covered_concerns.append(concern.concern_id)
        for task in retaining_tasks:
            if concern.domain == GENERAL_CONCERN_DOMAIN or task.domain == concern.domain:
                task_coverage[task.task_id]["concern_ids"].append(concern.concern_id)

    concern_ids = {item.concern_id for item in plan.concerns}
    for task in plan.tasks:
        for identifier in task.covers_concerns or []:
            if identifier not in concern_ids:
                errors.append(f"task {task.task_id} references unknown concern {identifier}")
            elif identifier not in task_coverage[task.task_id]["concern_ids"]:
                errors.append(f"task {task.task_id} does not retain concern {identifier} in its canonical domain")

    if _requests_supporting_evidence(plan):
        for task in plan.tasks:
            technical_subject = task.domain in detect_domains(task.goal) or bool(task_coverage[task.task_id]["concern_ids"])
            if technical_subject and not _meaningful_evidence_needs(task.evidence_needs):
                errors.append(f"task {task.task_id} requires subject-specific evidence_needs for requested supporting evidence")

    if missing_required:
        errors.append(
            "missing required obligation coverage: " + ", ".join(missing_required)
        )
    if missing_concerns:
        errors.append("missing concern coverage: " + ", ".join(missing_concerns))
    if misrouted_concerns:
        errors.append("misrouted concerns: " + ", ".join(misrouted_concerns))

    covered_obligation_set = set(covered_obligations)
    covered_obligations = [
        item.obligation_id
        for item in plan.obligations
        if item.obligation_id in covered_obligation_set
    ]
    return PlanVerification(
        valid=not errors,
        errors=tuple(dict.fromkeys(errors)),
        covered_obligations=tuple(covered_obligations),
        missing_required_obligations=tuple(missing_required),
        uncovered_optional_obligations=tuple(uncovered_optional),
        covered_concerns=tuple(covered_concerns),
        missing_concerns=tuple(missing_concerns),
        misrouted_concerns=tuple(misrouted_concerns),
        task_coverage=task_coverage,
    )


def validate_task_plan(
    plan: TaskPlan,
    *,
    coverage: Mapping[str, Iterable[str]] | None = None,
) -> PlanVerification:
    """Strictly validate a plan, raising with the structured report on failure."""

    report = verify_task_plan(plan, coverage=coverage)
    if not report.valid:
        raise TaskPlanValidationError(report)
    return report


def decide_repair(
    report: PlanVerification,
    *,
    repair_attempted: bool = False,
) -> RepairDecision:
    """Apply the one-bounded-repair policy to a verification result."""

    if report.valid:
        return RepairDecision("ACCEPT")
    if repair_attempted:
        return RepairDecision("REJECT", report.errors)
    return RepairDecision("REPAIR", report.errors)


def repair_preservation_contract(plan: TaskPlan, report: PlanVerification | None = None) -> dict:
    """Lock verified task content; leave only diagnosed defects editable."""
    report = report or verify_task_plan(plan)
    locks = []
    for task in plan.tasks:
        valid = report.task_coverage.get(task.task_id, {})
        if not any(valid.values()):
            continue
        lock = {"task_id": task.task_id, "domain": task.domain,
                "depends_on": list(task.depends_on), "goal_must_retain": task.goal,
                "covers_obligations": valid.get("obligation_ids", []),
                "covers_concerns": valid.get("concern_ids", [])}
        if _meaningful_evidence_needs(task.evidence_needs):
            lock["evidence_needs"] = list(task.evidence_needs)
        locks.append(lock)
    return {"preserve_tasks": locks, "diagnostics": list(report.errors)}


def validate_repaired_plan(
    original: TaskPlan,
    repaired: TaskPlan,
    *,
    coverage: Mapping[str, Iterable[str]] | None = None,
) -> PlanVerification:
    """Re-run all checks after repair and reject dropped request obligations.

    Invalid tasks may be corrected. Verified content and dependencies are locked;
    goals may be extended to cover the missing process/output obligations.
    """

    report = verify_task_plan(repaired, coverage=coverage)
    preservation_errors: list[str] = []
    if not isinstance(original, TaskPlan):
        preservation_errors.append("original plan must be a TaskPlan")
    elif not isinstance(repaired, TaskPlan):
        preservation_errors.append("repaired plan must be a TaskPlan")
    else:
        if original.request != repaired.request:
            preservation_errors.append("repair changed the request")
        if _obligation_signature(original) != _obligation_signature(repaired):
            preservation_errors.append("repair changed the obligations")
        if _concern_signature(original) != _concern_signature(repaired):
            preservation_errors.append("repair changed the concerns")
        repaired_tasks = {task.task_id: task for task in repaired.tasks}
        for lock in repair_preservation_contract(original)["preserve_tasks"]:
            task = repaired_tasks.get(lock["task_id"])
            if task is None:
                preservation_errors.append(f"repair dropped valid task {lock['task_id']}")
                continue
            for name in ("domain", "depends_on", "evidence_needs"):
                if name in lock and getattr(task, name) != lock[name]:
                    preservation_errors.append(f"repair changed valid {name} for task {task.task_id}")
            if " ".join(lock["goal_must_retain"].split()) not in " ".join(task.goal.split()):
                preservation_errors.append(f"repair lost valid goal content for task {task.task_id}")
            valid = report.task_coverage.get(task.task_id, {})
            for field_name, coverage_name in (("covers_obligations", "obligation_ids"), ("covers_concerns", "concern_ids")):
                if not set(lock[field_name]).issubset(valid.get(coverage_name, [])):
                    preservation_errors.append(f"repair lost valid {field_name} for task {task.task_id}")

    if not preservation_errors:
        return report
    return replace(
        report,
        valid=False,
        errors=tuple(dict.fromkeys((*report.errors, *preservation_errors))),
    )


# The longer name makes the post-repair boundary easy to find for callers that
# prefer an explicit verb; keep the primary API above concise.
post_repair_validate = validate_repaired_plan


def _validate_plan_shape(plan: TaskPlan) -> list[str]:
    errors: list[str] = []
    if not isinstance(plan.request, str) or not plan.request.strip():
        errors.append("TaskPlan.request must be a non-empty string")

    if not isinstance(plan.obligations, list):
        errors.append("TaskPlan.obligations must be a list")
    if not isinstance(plan.concerns, list):
        errors.append("TaskPlan.concerns must be a list")
    if not isinstance(plan.tasks, list):
        errors.append("TaskPlan.tasks must be a list")
    if errors:
        return errors

    obligation_ids: set[str] = set()
    for index, obligation in enumerate(plan.obligations):
        identifier = getattr(obligation, "obligation_id", None)
        description = getattr(obligation, "description", None)
        required = getattr(obligation, "required", None)
        if not isinstance(identifier, str) or not identifier.strip():
            errors.append(f"obligation {index} must have a non-empty obligation_id")
        elif identifier in obligation_ids:
            errors.append(f"duplicate obligation_id: {identifier}")
        else:
            obligation_ids.add(identifier)
        if not isinstance(description, str) or not description.strip():
            errors.append(f"obligation {identifier or index} description must be non-empty")
        if not isinstance(required, bool):
            errors.append(f"obligation {identifier or index} required must be a boolean")

    concern_ids: set[str] = set()
    for index, concern in enumerate(plan.concerns):
        identifier = getattr(concern, "concern_id", None)
        description = getattr(concern, "description", None)
        domain = getattr(concern, "domain", None)
        if not isinstance(identifier, str) or not identifier.strip():
            errors.append(f"concern {index} must have a non-empty concern_id")
        elif identifier in concern_ids:
            errors.append(f"duplicate concern_id: {identifier}")
        else:
            concern_ids.add(identifier)
        if not isinstance(description, str) or not description.strip():
            errors.append(f"concern {identifier or index} description must be non-empty")
        if not isinstance(domain, str) or not domain.strip():
            errors.append(f"concern {identifier or index} domain must be non-empty")
        elif domain != GENERAL_CONCERN_DOMAIN:
            try:
                validate_domain(domain)
            except ValueError as exc:
                errors.append(f"concern {identifier or index}: {exc}")

    for index, task in enumerate(plan.tasks):
        identifier = getattr(task, "task_id", None)
        goal = getattr(task, "goal", None)
        domain = getattr(task, "domain", None)
        dependencies = getattr(task, "depends_on", None)
        evidence_needs = getattr(task, "evidence_needs", None)
        if not isinstance(identifier, str) or not identifier.strip():
            errors.append(f"task {index} must have a non-empty task_id")
        if not isinstance(goal, str) or not goal.strip():
            errors.append(f"task {identifier or index} goal must be non-empty")
        if not isinstance(domain, str) or not domain.strip():
            errors.append(f"task {identifier or index} domain must be non-empty")
        if not isinstance(dependencies, list):
            errors.append(f"task {identifier or index} depends_on must be a list")
        else:
            for dependency in dependencies:
                if not isinstance(dependency, str) or not dependency.strip():
                    errors.append(
                        f"task {identifier or index} dependencies must be non-empty strings"
                    )
            if all(isinstance(dependency, str) for dependency in dependencies):
                if len(dependencies) != len(set(dependencies)):
                    errors.append(f"task {identifier or index} has duplicate dependencies")
        for name in ("covers_obligations", "covers_concerns"):
            raw_claims = getattr(task, name, None)
            if raw_claims is not None and not isinstance(raw_claims, list):
                errors.append(f"task {identifier or index} {name} must be a list")
            elif isinstance(raw_claims, list) and any(not isinstance(value, str) or not value.strip() for value in raw_claims):
                errors.append(f"task {identifier or index} {name} must contain non-empty IDs")
            elif isinstance(raw_claims, list) and len(raw_claims) != len(set(raw_claims)):
                errors.append(f"task {identifier or index} has duplicate coverage IDs")
            elif isinstance(raw_claims, list) and any(value != value.strip() for value in raw_claims):
                errors.append(f"task {identifier or index} has whitespace-padded coverage IDs")
        if not isinstance(evidence_needs, list) or any(not isinstance(value, str) or not value.strip() for value in evidence_needs):
            errors.append(f"task {identifier or index} evidence_needs must be a list of non-empty strings")

    if not plan.tasks:
        errors.append("TaskPlan.tasks must contain at least one task")
    return errors


def _normalize_coverage(
    coverage: Mapping[str, Iterable[str]] | None,
    task_ids: set[str],
) -> tuple[dict[str, list[str]], list[str]]:
    if coverage is None:
        return {}, []
    if not isinstance(coverage, Mapping):
        return {}, ["coverage must be a mapping of task IDs to obligation IDs"]

    errors: list[str] = []
    normalized: dict[str, list[str]] = {}
    for task_id, raw_ids in coverage.items():
        if task_id not in task_ids:
            errors.append(f"coverage references unknown task {task_id}")
            continue
        if isinstance(raw_ids, str) or not isinstance(raw_ids, Iterable):
            errors.append(f"coverage for task {task_id} must be an iterable of IDs")
            continue
        ids: list[str] = []
        for obligation_id in raw_ids:
            if not isinstance(obligation_id, str) or not obligation_id.strip():
                errors.append(f"coverage for task {task_id} contains an invalid obligation ID")
                continue
            clean_id = obligation_id.strip()
            if clean_id != obligation_id:
                errors.append(f"coverage for task {task_id} contains a whitespace-padded ID")
                continue
            if clean_id in ids:
                errors.append(f"coverage for task {task_id} contains duplicate ID {clean_id}")
                continue
            ids.append(clean_id)
        normalized[task_id] = ids
    return normalized, errors


def _string_ids(values: list[object]) -> list[str]:
    result: list[str] = []
    for value in values:
        if isinstance(value, str) and value.strip() and value.strip() not in result:
            result.append(value.strip())
    return result


def _task_text(task: object) -> str:
    fields = [getattr(task, "goal", "")]
    for name in ("title", "objective", "expected_output"):
        value = getattr(task, name, None)
        if isinstance(value, str):
            fields.append(value)
    return " ".join(value for value in fields if isinstance(value, str))


def _source_text(item: object) -> str:
    fields = [getattr(item, "description", "")]
    anchors = getattr(item, "anchors", None)
    if isinstance(anchors, list):
        fields.extend(anchor for anchor in anchors if isinstance(anchor, str))
    source_anchor = getattr(item, "source_anchor", None)
    if isinstance(source_anchor, str):
        fields.append(source_anchor)
    return " ".join(value for value in fields if isinstance(value, str))


def _concern_text_for_coverage(concern: object) -> str:
    """Drop the extractor's generic label before checking concern coverage."""

    text = _source_text(concern).strip()
    if text.casefold().startswith(_GENERAL_CONCERN_PREFIX):
        return text[len(_GENERAL_CONCERN_PREFIX) :]
    return text


def _retains_text(task_text: str, source_text: str) -> bool:
    task_terms = terms(task_text) - _LOW_SIGNAL_TERMS
    source_terms = terms(source_text) - _LOW_SIGNAL_TERMS
    if not task_terms or not source_terms:
        return False

    return source_terms.issubset(task_terms)


def _requests_supporting_evidence(plan: TaskPlan) -> bool:
    # An explicit positive retrieval/support clause, not a new obligation.
    descriptions = [item.description for item in plan.obligations if item.required]
    descriptions.extend(plan.request.split("."))
    for description in descriptions:
        words = terms(description)
        negative_action = re.search(
            r"\b(?:not|never|without)\s+(?:retrieve|retrieving|include|including|provide|providing|cite|citing|use|using)\b",
            description, re.IGNORECASE,
        )
        if words & terms("evidence citation citations source sources") and words & terms("retrieve retrieval supporting cite grounded include provide use") and not negative_action:
            return True
    return False


def _meaningful_evidence_needs(values: list[str]) -> bool:
    generic = terms("evidence source sources relevant supporting planning context document task user request")
    return any(
        terms(value) - generic
        for value in values
        if not value.startswith("src_") and not re.fullmatch(r"[OCTE]\d+", value.strip(), re.IGNORECASE)
    )


def _obligation_signature(plan: TaskPlan) -> tuple[tuple[str, str, bool], ...]:
    return tuple(
        sorted(
            (
                item.obligation_id,
                _source_text(item),
                item.required,
            )
            for item in plan.obligations
        )
    )


def _concern_signature(plan: TaskPlan) -> tuple[tuple[str, str, str], ...]:
    return tuple(
        sorted(
            (
                item.concern_id,
                _source_text(item),
                item.domain,
            )
            for item in plan.concerns
        )
    )


__all__ = [
    "GENERAL_CONCERN_DOMAIN",
    "PlanVerification",
    "RepairAction",
    "RepairDecision",
    "TaskPlanValidationError",
    "decide_repair",
    "post_repair_validate",
    "validate_repaired_plan",
    "validate_task_plan",
    "verify_task_plan",
]
