"""Typed boundary for persisted research runs.

The runtime historically persisted dictionaries. ``Run`` is a compatibility
wrapper around that exact shape: unknown keys are retained so existing traces
and future additive metadata are never discarded.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, ClassVar, Mapping


@dataclass(frozen=True)
class Run:
    run_id: str
    created_at: str | None = None
    condition: str | None = None
    implementation_profile: str | None = None
    provider: str | None = None
    model: str | None = None
    query: str | None = None
    conversation_id: str | None = None
    conversation_context: Any = None
    status: str | None = None
    answer: str | None = None
    source_snapshot_id: str | None = None
    config_hash: str | None = None
    tasks: list[dict[str, Any]] = field(default_factory=list)
    task_results: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    effective_config: dict[str, Any] = field(default_factory=dict)
    scoring_versions: dict[str, Any] = field(default_factory=dict)
    planning_retrieval_scoring_version: str | None = None
    retrieval_scoring_version: str | None = None
    domain_ranking_version: str | None = None
    retrieval: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict, repr=False)

    FIELDS: ClassVar[tuple[str, ...]] = (
        "run_id", "created_at", "condition", "implementation_profile",
        "provider", "model", "query", "conversation_id",
        "conversation_context", "status", "answer", "source_snapshot_id",
        "config_hash", "tasks", "task_results", "metrics", "events",
        "effective_config", "scoring_versions",
        "planning_retrieval_scoring_version", "retrieval_scoring_version",
        "domain_ranking_version", "retrieval",
    )

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "Run":
        if not isinstance(value, Mapping):
            raise TypeError("run must be a mapping")
        run_id = value.get("run_id")
        if not isinstance(run_id, str) or not run_id:
            raise ValueError("run_id is required")
        known = {
            key: deepcopy(value[key])
            for key in cls.FIELDS
            if key in value
        }
        extra = {
            key: deepcopy(item)
            for key, item in value.items()
            if key not in cls.FIELDS
        }
        return cls(**known, extra=extra)

    def to_dict(self) -> dict[str, Any]:
        result = deepcopy(self.extra)
        for key in self.FIELDS:
            result[key] = deepcopy(getattr(self, key))
        return result


__all__ = ["Run"]
