"""Deterministic Task Coverage for the Sprint 3 P-lite pilot.

The metric measures structural coverage only.  It does not infer research
correctness from task text or model self-reports: task-to-obligation matches
must be supplied by an independent evaluator.

Input is a case's frozen ``gold_obligation_ids`` and a mapping from reviewed
task IDs to the gold obligations those tasks were judged to serve.  Output is
``TaskCoverageResult`` with ``value = covered / total`` when the annotation is
complete, a marked lower bound when it is partial, and ``value=None`` when the
measurement is undefined.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Literal


DEFINED: Literal["DEFINED"] = "DEFINED"
PARTIAL: Literal["PARTIAL"] = "PARTIAL"
UNDEFINED: Literal["UNDEFINED"] = "UNDEFINED"
CoverageStatus = Literal["DEFINED", "PARTIAL", "UNDEFINED"]


@dataclass(frozen=True)
class TaskCoverageResult:
    """One case-level result without making a correctness claim."""

    status: CoverageStatus
    value: float | None
    total_obligations: int
    covered_obligation_ids: tuple[str, ...] = ()
    uncovered_obligation_ids: tuple[str, ...] = ()
    unassessed_obligation_ids: tuple[str, ...] = ()
    annotated_task_count: int = 0
    annotations_complete: bool | None = None
    reason: str | None = None
    is_lower_bound: bool = False

    @property
    def covered_count(self) -> int:
        """Return the number of distinct covered gold obligations."""

        return len(self.covered_obligation_ids)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-friendly representation that preserves state."""

        return {
            "metric": "task_coverage",
            "status": self.status,
            "value": self.value,
            "covered_obligations": self.covered_count,
            "total_obligations": self.total_obligations,
            "covered_obligation_ids": list(self.covered_obligation_ids),
            "uncovered_obligation_ids": list(self.uncovered_obligation_ids),
            "unassessed_obligation_ids": list(self.unassessed_obligation_ids),
            "annotated_task_count": self.annotated_task_count,
            "annotations_complete": self.annotations_complete,
            "is_lower_bound": self.is_lower_bound,
            "reason": self.reason,
        }


def _normalise_ids(values: Iterable[str], field_name: str) -> tuple[str, ...]:
    """Validate IDs and return a deterministic duplicate-free tuple."""

    if isinstance(values, (str, bytes)):
        raise TypeError(f"{field_name} must be an iterable of IDs, not a string")
    try:
        raw_values = list(values)
    except TypeError as exc:
        raise TypeError(f"{field_name} must be an iterable of string IDs") from exc

    result: set[str] = set()
    for value in raw_values:
        if not isinstance(value, str):
            raise TypeError(f"{field_name} must contain only string IDs")
        value = value.strip()
        if not value:
            raise ValueError(f"{field_name} must not contain empty IDs")
        result.add(value)
    return tuple(sorted(result))


def _undefined(
    total_obligations: int,
    unassessed_obligation_ids: tuple[str, ...],
    reason: str,
) -> TaskCoverageResult:
    return TaskCoverageResult(
        status=UNDEFINED,
        value=None,
        total_obligations=total_obligations,
        unassessed_obligation_ids=unassessed_obligation_ids,
        reason=reason,
    )


def calculate_task_coverage(
    gold_obligation_ids: Iterable[str] | None,
    annotated_task_matches: Mapping[str, Iterable[str] | None] | None,
    *,
    annotations_complete: bool = True,
) -> TaskCoverageResult:
    """Calculate Task Coverage from independent task-match annotations.

    ``gold_obligation_ids`` is the frozen gold denominator.  Each value in
    ``annotated_task_matches`` is a set/list of gold IDs independently judged
    to be served by that task; it is not a field read from the generated task.
    ``None`` for the mapping means annotations are unavailable, while ``{}``
    means a complete reviewed plan with no matches.  Set
    ``annotations_complete=False`` for a partial review; its value is then a
    lower bound and remaining obligations are unassessed, not uncovered.

    Missing gold or annotations returns ``UNDEFINED`` with ``value=None``.
    Invalid IDs raise instead of silently changing the denominator.
    """

    if not isinstance(annotations_complete, bool):
        raise TypeError("annotations_complete must be a bool")
    if gold_obligation_ids is None:
        return _undefined(0, (), "gold obligations are unavailable")

    gold_ids = _normalise_ids(gold_obligation_ids, "gold_obligation_ids")
    if not gold_ids:
        return _undefined(0, (), "the case has no gold obligations")
    if annotated_task_matches is None:
        return _undefined(
            len(gold_ids),
            gold_ids,
            "independent task-match annotations are unavailable",
        )
    if not isinstance(annotated_task_matches, Mapping):
        raise TypeError("annotated_task_matches must be a mapping")

    matched_ids: set[str] = set()
    for task_id, obligation_ids in annotated_task_matches.items():
        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError("annotated_task_matches keys must be non-empty strings")
        if obligation_ids is None:
            if annotations_complete:
                raise ValueError(
                    "a complete annotation cannot contain a missing task-match list"
                )
            continue
        matched_ids.update(
            _normalise_ids(obligation_ids, f"matches for task {task_id!r}")
        )

    unknown_ids = matched_ids.difference(gold_ids)
    if unknown_ids:
        raise ValueError(
            "task matches reference unknown gold obligations: "
            + ", ".join(sorted(unknown_ids))
        )

    covered_ids = tuple(sorted(matched_ids))
    value = len(covered_ids) / len(gold_ids)
    common = {
        "value": value,
        "total_obligations": len(gold_ids),
        "covered_obligation_ids": covered_ids,
        "annotated_task_count": len(annotated_task_matches),
        "annotations_complete": annotations_complete,
    }

    if annotations_complete:
        return TaskCoverageResult(
            status=DEFINED,
            uncovered_obligation_ids=tuple(sorted(set(gold_ids) - matched_ids)),
            **common,
        )

    return TaskCoverageResult(
        status=PARTIAL,
        unassessed_obligation_ids=tuple(sorted(set(gold_ids) - matched_ids)),
        reason="task-match annotation is incomplete; value is a lower bound",
        is_lower_bound=True,
        **common,
    )


__all__ = [
    "DEFINED",
    "PARTIAL",
    "UNDEFINED",
    "CoverageStatus",
    "TaskCoverageResult",
    "calculate_task_coverage",
]
