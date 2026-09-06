import json
from pathlib import Path

import pytest

from app.planning.kb import (
    DEFAULT_DATASET_PATH,
    REQUIRED_FIELDS,
    load_planning_kb,
)


def _field(item, name: str):
    try:
        return getattr(item, name)
    except AttributeError:
        return item[name]


def test_loads_curated_items_with_stable_ids_and_provenance():
    first = load_planning_kb()
    second = load_planning_kb()

    assert DEFAULT_DATASET_PATH.name == "p_lite_items.json"
    assert first == second
    assert len(first) == 4
    assert len({_field(item, "id") for item in first}) == len(first)
    assert all(_field(item, "provenance").startswith("datasets/planning/") for item in first)
    assert all(
        set(item) == set(REQUIRED_FIELDS)
        if isinstance(item, dict)
        else all(hasattr(item, field) for field in REQUIRED_FIELDS)
        for item in first
    )


def test_planning_items_are_guidance_not_domain_source_chunks():
    items = load_planning_kb()

    assert all("gold" not in _field(item, "content").casefold() for item in items)
    assert all("answer" not in _field(item, "content").casefold() for item in items)
    assert all(not hasattr(item, "chunk_id") for item in items)


def test_loader_rejects_duplicate_ids_and_over_bound_dataset(tmp_path: Path):
    duplicate_path = tmp_path / "duplicate.json"
    duplicate_path.write_text(
        json.dumps(
            [
                {
                    "id": "same",
                    "domain": "security",
                    "title": "One",
                    "content": "Guidance one",
                    "provenance": "local#one",
                },
                {
                    "id": "same",
                    "domain": "database",
                    "title": "Two",
                    "content": "Guidance two",
                    "provenance": "local#two",
                },
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate item id"):
        load_planning_kb(duplicate_path)

    with pytest.raises(ValueError, match="max_items"):
        load_planning_kb(DEFAULT_DATASET_PATH, max_items=3)


def test_loader_rejects_contract_shape_errors(tmp_path: Path):
    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text(
        json.dumps(
            [
                {
                    "id": "invalid",
                    "domain": "security",
                    "title": "",
                    "content": "Guidance",
                    "provenance": "local#invalid",
                }
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="title.*non-empty string"):
        load_planning_kb(invalid_path)
