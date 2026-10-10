"""Read-only consistency checks for persisted run traces and metrics."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def compare_trace_and_metrics(attempt: Mapping[str, Any]) -> dict[str, bool | None]:
    """Compare fields already persisted on one attempt without grading it.

    A ``None`` result means the attempt did not persist enough information for
    that comparison. This helper neither derives nor changes research metrics.
    """

    events = attempt.get("events")
    events = [event for event in events if isinstance(event, Mapping)] if isinstance(events, list) else []
    metrics = attempt.get("metrics")
    metrics = metrics if isinstance(metrics, Mapping) else {}

    return {
        "terminal_status_matches_trace": _terminal_status_matches_trace(
            attempt.get("status"), events
        ),
        "token_totals_match": _token_totals_match(metrics),
        "task_retrieval_counts_match": _task_retrieval_counts_match(events, metrics),
    }


def _terminal_status_matches_trace(status: Any, events: list[Mapping[str, Any]]) -> bool | None:
    if not isinstance(status, str):
        return None

    terminal_events = [
        event for event in events
        if event.get("stage") in {"run_finished", "run_failed", "retrieval_failed", "runner_failed"}
    ]
    if not terminal_events:
        return None

    last_terminal = terminal_events[-1]
    stage = last_terminal.get("stage")
    if stage == "run_finished":
        trace_status = last_terminal.get("status")
        return trace_status == status if isinstance(trace_status, str) else None
    return status == "FAILED"


def _token_totals_match(metrics: Mapping[str, Any]) -> bool | None:
    input_tokens = metrics.get("input_tokens")
    output_tokens = metrics.get("output_tokens")
    total_tokens = metrics.get("total_tokens")
    values = (input_tokens, output_tokens, total_tokens)
    if not all(isinstance(value, int) and not isinstance(value, bool) for value in values):
        return None
    return input_tokens + output_tokens == total_tokens


def _task_retrieval_counts_match(
    events: list[Mapping[str, Any]], metrics: Mapping[str, Any]
) -> bool | None:
    retrieval_events = [event for event in events if event.get("stage") == "task_retrieval"]
    if not retrieval_events:
        return None

    fields = ("candidates", "selected", "dropped")
    if any(not all(isinstance(event.get(field), list) for field in fields) for event in retrieval_events):
        return None

    metric_fields = ("retrieved_chunks", "selected_chunks", "dropped_chunks")
    metric_values = tuple(metrics.get(field) for field in metric_fields)
    if not all(isinstance(value, int) and not isinstance(value, bool) for value in metric_values):
        return None

    trace_counts = (
        sum(len(event["candidates"]) for event in retrieval_events),
        sum(len(event["selected"]) for event in retrieval_events),
        sum(len(event["dropped"]) for event in retrieval_events),
    )
    return trace_counts == metric_values
