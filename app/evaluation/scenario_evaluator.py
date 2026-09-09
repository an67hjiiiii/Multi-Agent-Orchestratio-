"""Scenario-level, post-inference evaluation helpers.

The generation runner deliberately receives request fields only.  This module
joins a terminal run with scenario gold *after* inference and exposes the
gold fields to a human/independent evaluator without pretending that
citations, task names, or model self-reports prove semantic correctness.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from app.evaluation.final_experiment import evaluate_after_inference
from app.evaluation.task_coverage import calculate_task_coverage

SCENARIO_EVALUATION_SCHEMA = "scenario-gold-evaluation-v1"
PENDING_HUMAN_REVIEW = "PENDING_HUMAN_REVIEW"


def build_case_gold_index(
    benchmark_payload: Mapping[str, Any], gold_payload: Mapping[str, Any]
) -> dict[str, Mapping[str, Any]]:
    """Map frozen request variant IDs to their scenario-level gold row.

    The benchmark remains the source of variant membership.  No request or
    gold value is modified, and a malformed/ambiguous mapping fails closed.
    """

    groups = benchmark_payload.get("scenario_groups")
    gold_rows = gold_payload.get("scenario_gold")
    if not isinstance(groups, list) or not isinstance(gold_rows, list):
        raise ValueError("benchmark and gold payloads must contain scenario lists")

    gold_by_group: dict[str, Mapping[str, Any]] = {}
    for row in gold_rows:
        if not isinstance(row, Mapping):
            raise ValueError("scenario gold rows must be objects")
        group_id = row.get("scenario_group_id")
        if not isinstance(group_id, str) or not group_id:
            raise ValueError("scenario gold row requires scenario_group_id")
        if group_id in gold_by_group:
            raise ValueError(f"duplicate scenario gold group: {group_id}")
        gold_by_group[group_id] = row

    case_index: dict[str, Mapping[str, Any]] = {}
    for group in groups:
        if not isinstance(group, Mapping):
            raise ValueError("scenario groups must be objects")
        group_id = group.get("scenario_group_id")
        if not isinstance(group_id, str) or not group_id:
            raise ValueError("scenario group requires scenario_group_id")
        gold = gold_by_group.get(group_id)
        if gold is None:
            raise ValueError(f"missing scenario gold for group: {group_id}")
        variants = group.get("variants")
        if not isinstance(variants, list) or not variants:
            raise ValueError(f"scenario group has no variants: {group_id}")
        for variant in variants:
            if not isinstance(variant, Mapping):
                raise ValueError("scenario variants must be objects")
            case_id = variant.get("case_id")
            if not isinstance(case_id, str) or not case_id:
                raise ValueError(f"scenario variant requires case_id: {group_id}")
            if case_id in case_index:
                raise ValueError(f"duplicate case_id in benchmark: {case_id}")
            case_index[case_id] = gold
    return case_index


def _event_rows(row: Mapping[str, Any], stage: str) -> list[Mapping[str, Any]]:
    events = row.get("events")
    if not isinstance(events, list):
        return []
    return [item for item in events if isinstance(item, Mapping) and item.get("stage") == stage]


def _string_ids(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    result: set[str] = set()
    for item in value:
        if isinstance(item, str) and item:
            result.add(item)
        elif isinstance(item, Mapping):
            chunk_id = item.get("chunk_id")
            if isinstance(chunk_id, str) and chunk_id:
                result.add(chunk_id)
    return result


def _retrieval_ids(row: Mapping[str, Any], field: str) -> set[str]:
    values: set[str] = set()
    for stage in ("vanilla_retrieval", "task_retrieval"):
        for event in _event_rows(row, stage):
            values.update(_string_ids(event.get(field)))
    return values


def _trace_records(
    row: Mapping[str, Any], stage: str, field: str
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for event in _event_rows(row, stage):
        values = event.get(field)
        if not isinstance(values, list):
            continue
        for value in values:
            if isinstance(value, Mapping):
                records.append(dict(value))
            elif isinstance(value, str) and value:
                records.append({"chunk_id": value})
    return records


def _dependency_graph_valid(tasks: Any) -> bool | None:
    if not isinstance(tasks, list):
        return None
    ids: list[str] = []
    dependencies: dict[str, list[str]] = {}
    for task in tasks:
        if not isinstance(task, Mapping):
            return False
        task_id = task.get("task_id")
        depends_on = task.get("depends_on", [])
        if not isinstance(task_id, str) or not task_id or not isinstance(depends_on, list):
            return False
        if task_id in dependencies:
            return False
        ids.append(task_id)
        dependencies[task_id] = [item for item in depends_on if isinstance(item, str)]
        if len(dependencies[task_id]) != len(depends_on):
            return False
    known = set(ids)
    if any(dep == task_id or dep not in known for task_id, deps in dependencies.items() for dep in deps):
        return False

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> bool:
        if task_id in visiting:
            return False
        if task_id in visited:
            return True
        visiting.add(task_id)
        if not all(visit(dep) for dep in dependencies[task_id]):
            return False
        visiting.remove(task_id)
        visited.add(task_id)
        return True

    return all(visit(task_id) for task_id in ids)


def _condition_trace(row: Mapping[str, Any]) -> dict[str, Any]:
    expected_flags = {
        "A": {"P": False, "N": False, "O": False},
        "B": {"P": False, "N": False, "O": False},
        "C": {"P": True, "N": True, "O": True},
        "C-P": {"P": False, "N": True, "O": True},
        "C-N": {"P": True, "N": False, "O": True},
        "C-O": {"P": True, "N": True, "O": False},
    }
    condition = str(row.get("condition") or "")
    flags: Mapping[str, Any] = {}
    for event in _event_rows(row, "run_started"):
        if isinstance(event.get("flags"), Mapping):
            flags = event["flags"]
            break
    if not flags and isinstance(row.get("effective_config"), Mapping):
        configured = row["effective_config"].get("flags")
        if isinstance(configured, Mapping):
            flags = configured
    observed_flags = {name: bool(flags.get(name)) for name in ("P", "N", "O")}
    stages = {stage: bool(_event_rows(row, stage)) for stage in (
        "planning_retrieval",
        "decomposition",
        "normalization",
        "task_retrieval",
        "overlap_summary",
    )}
    return {
        "declared_condition": condition,
        "observed_flags": observed_flags,
        "expected_flags": expected_flags.get(condition),
        "flags_match_condition": expected_flags.get(condition) == observed_flags,
        "stages": stages,
    }


def _citation_snapshot(row: Mapping[str, Any]) -> dict[str, Any]:
    metrics = row.get("metrics") if isinstance(row.get("metrics"), Mapping) else {}
    snapshot = row.get("metric_snapshot")
    if isinstance(snapshot, Mapping):
        source = snapshot
    else:
        source = metrics
    emitted = source.get("citations_emitted")
    valid = source.get("citations_valid")
    locator = source.get("citation_locator_validity")
    if locator is None and isinstance(emitted, (int, float)) and emitted:
        if isinstance(valid, (int, float)):
            locator = round(valid / emitted, 4)
    return {
        "citations_emitted": emitted,
        "citations_valid": valid,
        "citation_locator_validity": locator,
        "semantic_grounding": PENDING_HUMAN_REVIEW,
    }


def _coverage_from_annotations(
    case_id: str, annotations: Mapping[str, Any] | None
) -> dict[str, Any]:
    if not isinstance(annotations, Mapping):
        return {
            "status": "UNDEFINED",
            "value": None,
            "reason": "independent task-match annotations are unavailable",
        }
    case_annotation = annotations.get(case_id, annotations)
    if not isinstance(case_annotation, Mapping):
        return {
            "status": "UNDEFINED",
            "value": None,
            "reason": "independent task-match annotations are unavailable",
        }
    gold_ids = case_annotation.get("gold_obligation_ids")
    task_matches = case_annotation.get("task_matches")
    if gold_ids is None or task_matches is None:
        return {
            "status": "UNDEFINED",
            "value": None,
            "reason": "gold obligation IDs/task matches are unavailable",
        }
    result = calculate_task_coverage(
        gold_ids,
        task_matches,
        annotations_complete=bool(case_annotation.get("annotations_complete", True)),
    )
    return result.to_dict()


def build_scenario_evaluation_row(
    attempt: Mapping[str, Any],
    gold: Mapping[str, Any],
    *,
    annotations: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one evaluator-facing row from a terminal attempt and gold.

    Automatic values are limited to structural/telemetry checks.  Semantic
    answer points, role judgments, dependency meaning, normalization meaning,
    overlap necessity, and faithfulness remain explicitly human-owned.
    """

    case_id = str(attempt.get("case_id") or "")
    gold_evidence = _string_ids(gold.get("relevant_evidence_ids"))
    candidates = _retrieval_ids(attempt, "candidates")
    selected = _retrieval_ids(attempt, "selected")
    dropped = _retrieval_ids(attempt, "dropped")
    task_retrieval_events = _event_rows(attempt, "task_retrieval")
    planning_evidence_ids: set[str] = set()
    for event in _event_rows(attempt, "planning_retrieval"):
        planning_evidence_ids.update(_string_ids(event.get("selected")))
    shared: set[str] = set()
    for event in task_retrieval_events:
        shared.update(_string_ids(event.get("shared_evidence_ids")))
    metrics = attempt.get("metrics") if isinstance(attempt.get("metrics"), Mapping) else {}
    metric_snapshot = attempt.get("metric_snapshot")
    if isinstance(metric_snapshot, Mapping):
        metrics = metric_snapshot
    recall = None
    selected_recall = None
    if gold_evidence:
        recall = round(len(gold_evidence.intersection(candidates)) / len(gold_evidence), 4)
        selected_recall = round(len(gold_evidence.intersection(selected)) / len(gold_evidence), 4)
    tasks = attempt.get("tasks")
    task_results = attempt.get("task_results")
    observed_missing_information: list[str] = []
    observed_status_reasons: list[dict[str, Any]] = []
    if isinstance(task_results, list):
        for result in task_results:
            if not isinstance(result, Mapping):
                continue
            observed_missing_information.extend(
                item
                for item in result.get("missing_information", [])
                if isinstance(item, str) and item
            )
            task_id = result.get("task_id")
            status_reason = result.get("status_reason")
            if isinstance(task_id, str) and isinstance(status_reason, str) and status_reason:
                observed_status_reasons.append(
                    {"task_id": task_id, "status_reason": status_reason}
                )
    normalization_trace = [
        dict(item)
        for event in _event_rows(attempt, "normalization")
        for item in (event.get("trace") or [])
        if isinstance(item, Mapping)
    ]
    overlap_summaries = [
        dict(event) for event in _event_rows(attempt, "overlap_summary")
    ]
    return {
        "evaluation_schema": SCENARIO_EVALUATION_SCHEMA,
        "scenario_group_id": gold.get("scenario_group_id"),
        "scenario_gold_id": gold.get("scenario_gold_id"),
        "reviewer_status": gold.get("reviewer_status", PENDING_HUMAN_REVIEW),
        "observed": {
            "status": attempt.get("status"),
            "task_count": len(tasks) if isinstance(tasks, list) else None,
            "task_ids": [task.get("task_id") for task in tasks if isinstance(task, Mapping)] if isinstance(tasks, list) else [],
            "dependency_graph_valid": _dependency_graph_valid(tasks),
            "retrieved_evidence_ids": sorted(candidates),
            "selected_evidence_ids": sorted(selected),
            "dropped_evidence_ids": sorted(dropped),
            "dropped_evidence": _trace_records(attempt, "task_retrieval", "dropped"),
            "selected_evidence": _trace_records(
                attempt, "task_retrieval", "selected_evidence"
            ),
            "planning_evidence_ids": sorted(planning_evidence_ids),
            "shared_evidence_ids": sorted(shared),
            "normalization_trace": normalization_trace,
            "overlap_summaries": overlap_summaries,
            "missing_information": observed_missing_information,
            "status_reasons": observed_status_reasons,
            "metrics": dict(metrics),
            "citation": _citation_snapshot(attempt),
        },
        "automatic": {
            "candidate_evidence_recall_at_k": recall,
            "selected_evidence_recall": selected_recall,
            "condition_trace": _condition_trace(attempt),
        },
        "gold_reference": {
            "expected_status": gold.get("expected_status"),
            "expected_role": gold.get("expected_role"),
            "expected_roles": gold.get("expected_roles", []),
            "expected_domain": gold.get("expected_domain"),
            "expected_domains": gold.get("expected_domains", []),
            "relevant_evidence_ids": sorted(gold_evidence),
            "expected_answer_points": gold.get("expected_answer_points", []),
            "expected_missing_information": gold.get("expected_missing_information"),
            "dependency_expectation": gold.get("dependency_expectation"),
            "normalization_expectation": gold.get("normalization_expectation"),
            "overlap_expectation": gold.get("overlap_expectation"),
        },
        "human_evaluation": {
            "task_coverage": _coverage_from_annotations(case_id, annotations),
            "answer_points": PENDING_HUMAN_REVIEW,
            "role_assignment": PENDING_HUMAN_REVIEW,
            "dependency_semantics": PENDING_HUMAN_REVIEW,
            "normalization_semantics": PENDING_HUMAN_REVIEW,
            "overlap_necessity": PENDING_HUMAN_REVIEW,
            "answer_quality": PENDING_HUMAN_REVIEW,
            "faithfulness": PENDING_HUMAN_REVIEW,
        },
    }


def evaluate_scenario_gold_after_inference(
    report_path: str | Path,
    benchmark_loader: Callable[[], Mapping[str, Any]],
    gold_loader: Callable[[], Mapping[str, Any]],
    *,
    annotations_loader: Callable[[], Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Join scenario gold only after terminal inference is verified."""

    def load_bundle() -> dict[str, Any]:
        bundle: dict[str, Any] = {
            "benchmark": benchmark_loader(),
            "gold": gold_loader(),
        }
        if annotations_loader is not None:
            bundle["annotations"] = annotations_loader()
        return bundle

    index: dict[str, Mapping[str, Any]] | None = None

    def score(row: dict[str, Any], bundle: Mapping[str, Any]) -> Mapping[str, Any]:
        nonlocal index
        if index is None:
            index = build_case_gold_index(bundle["benchmark"], bundle["gold"])
        case_id = str(row.get("case_id") or "")
        gold = index.get(case_id)
        if gold is None:
            raise ValueError(f"no scenario gold for terminal case: {case_id}")
        annotations = bundle.get("annotations")
        return build_scenario_evaluation_row(
            row,
            gold,
            annotations=annotations if isinstance(annotations, Mapping) else None,
        )

    return evaluate_after_inference(report_path, load_bundle, scorer=score)


__all__ = [
    "PENDING_HUMAN_REVIEW",
    "SCENARIO_EVALUATION_SCHEMA",
    "build_case_gold_index",
    "build_scenario_evaluation_row",
    "evaluate_scenario_gold_after_inference",
]
