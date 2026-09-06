"""Load the curated local Planning KB used by Sprint 3 P-lite.

Planning items are decomposition guidance only.  They are intentionally kept
separate from the Domain KB and must never be used as answer-domain evidence.
The loader reads a small checked-in JSON file and performs deterministic shape,
identity, and size validation before returning its items.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET_PATH = PROJECT_ROOT / "datasets" / "planning" / "p_lite_items.json"

REQUIRED_FIELDS = ("id", "domain", "title", "content", "provenance")

# These caps keep a malformed or accidentally expanded local file from
# becoming an unbounded planning prompt.  The P-lite retriever may apply a
# smaller per-request cap later.
DEFAULT_MAX_ITEMS = 16
MAX_DATASET_BYTES = 128 * 1024
MAX_ITEM_CONTENT_CHARS = 4_000
MAX_TOTAL_CONTENT_CHARS = 16_000


def _validate_max_items(max_items: int) -> None:
    if isinstance(max_items, bool) or not isinstance(max_items, int) or max_items < 1:
        raise ValueError("max_items must be a positive integer")


def _read_records(path: Path) -> list[object]:
    try:
        file_size = path.stat().st_size
    except OSError as exc:
        raise ValueError(f"unable to read planning KB: {path}") from exc
    if file_size > MAX_DATASET_BYTES:
        raise ValueError(
            f"planning KB exceeds the {MAX_DATASET_BYTES}-byte file cap"
        )

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ValueError(f"planning KB is not valid UTF-8 JSON: {path}") from exc
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"planning KB is not valid UTF-8 JSON: {path}") from exc

    if not isinstance(payload, list):
        raise ValueError("planning KB root must be a JSON array")
    return payload


def _contract_model() -> type[Any] | None:
    """Return the shared contract model when the research worker has added it.

    Member 4 owns the contract model.  This base commit does not contain it,
    so validated mappings are returned until the integration worker wires that
    model into the loader.
    """

    try:
        from app.research.task_schema import PlanningKnowledgeItem
    except ImportError:
        return None
    return PlanningKnowledgeItem


def _validate_record(raw: object, position: int, seen_ids: set[str]) -> dict[str, str]:
    if not isinstance(raw, Mapping):
        raise ValueError(f"planning KB item {position} must be a JSON object")

    keys = set(raw)
    required = set(REQUIRED_FIELDS)
    missing = sorted(required.difference(keys))
    extra = sorted(keys.difference(required))
    if missing or extra:
        details: list[str] = []
        if missing:
            details.append(f"missing fields: {', '.join(missing)}")
        if extra:
            details.append(f"unexpected fields: {', '.join(extra)}")
        raise ValueError(f"planning KB item {position} has invalid shape ({'; '.join(details)})")

    record: dict[str, str] = {}
    for field in REQUIRED_FIELDS:
        value = raw[field]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"planning KB item {position} field {field!r} must be a non-empty string"
            )
        record[field] = value.strip()

    item_id = record["id"]
    if item_id in seen_ids:
        raise ValueError(f"planning KB contains duplicate item id {item_id!r}")
    seen_ids.add(item_id)
    return record


def load_planning_kb(
    path: str | Path = DEFAULT_DATASET_PATH,
    *,
    max_items: int = DEFAULT_MAX_ITEMS,
) -> list[Any]:
    """Load validated P-lite items from the checked-in local dataset.

    Items retain the JSON order so repeated loads are stable and easy to
    inspect.  If the shared ``PlanningKnowledgeItem`` model is available, each
    mapping is constructed with that model.  Otherwise, the validated mapping
    is returned for the domain integrator to adapt without duplicating the
    contract in this storage module.
    """

    _validate_max_items(max_items)
    dataset_path = Path(path)
    records = _read_records(dataset_path)
    if len(records) > max_items:
        raise ValueError(
            f"planning KB contains {len(records)} items; max_items is {max_items}"
        )

    seen_ids: set[str] = set()
    validated: list[dict[str, str]] = []
    total_content_chars = 0
    for position, raw in enumerate(records):
        record = _validate_record(raw, position, seen_ids)
        content_length = len(record["content"])
        if content_length > MAX_ITEM_CONTENT_CHARS:
            raise ValueError(
                f"planning KB item {record['id']!r} exceeds the "
                f"{MAX_ITEM_CONTENT_CHARS}-character content cap"
            )
        total_content_chars += content_length
        if total_content_chars > MAX_TOTAL_CONTENT_CHARS:
            raise ValueError(
                f"planning KB exceeds the {MAX_TOTAL_CONTENT_CHARS}-character "
                "total content cap"
            )
        validated.append(record)

    model = _contract_model()
    if model is None:
        return [dict(record) for record in validated]

    result: list[Any] = []
    for record in validated:
        try:
            result.append(model(**record))
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"planning KB item {record['id']!r} does not satisfy "
                "PlanningKnowledgeItem"
            ) from exc
    return result


def load_planning_items(
    path: str | Path = DEFAULT_DATASET_PATH,
    *,
    max_items: int = DEFAULT_MAX_ITEMS,
) -> list[Any]:
    """Compatibility name for integrations that refer to the item loader."""

    return load_planning_kb(path, max_items=max_items)


__all__ = [
    "DEFAULT_DATASET_PATH",
    "DEFAULT_MAX_ITEMS",
    "MAX_DATASET_BYTES",
    "MAX_ITEM_CONTENT_CHARS",
    "MAX_TOTAL_CONTENT_CHARS",
    "REQUIRED_FIELDS",
    "load_planning_items",
    "load_planning_kb",
]
