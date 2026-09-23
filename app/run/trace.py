"""Raw persisted run-event helpers.

Events remain append-only dictionaries so existing run artifacts and API
responses retain their wire shape.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any


def append_run_event(events: list[dict[str, Any]], stage: str, **data: Any) -> None:
    """Append one timestamped event without reshaping its caller-owned payload."""

    events.append(
        {"stage": stage, "ts": datetime.now(timezone.utc).isoformat(), **data}
    )


def persisted_run_events(run: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Read current events or the legacy trace field, preserving mapping rows only."""

    events = run.get("events")
    if not isinstance(events, list):
        events = run.get("trace")
    if not isinstance(events, list):
        return []
    return [dict(item) for item in events if isinstance(item, Mapping)]
