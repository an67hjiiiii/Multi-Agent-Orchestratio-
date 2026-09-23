"""Compatibility exports for runtime Task Normalization (N)."""

from app.orchestration.normalization import normalize_tasks, normalize_tasks_with_trace

__all__ = ["normalize_tasks", "normalize_tasks_with_trace"]
