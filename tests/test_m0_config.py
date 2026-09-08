from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.config import CONDITION_DEFINITIONS, RuntimeConfig


CONFIG_ENV_VARS = (
    "IMPLEMENTATION_PROFILE",
    "PROVIDER",
    "LOCAL_LLM_MODEL",
    "TASK_TOP_K",
    "PLANNING_TOP_K",
    "MAX_CONTEXT_TOKENS",
    "MAX_OUTPUT_TOKENS",
    "MAX_RUN_TOKENS",
    "RETRY_LIMIT",
    "MIN_RETRIEVAL_SCORE",
)


def make_m0_config(monkeypatch: pytest.MonkeyPatch) -> RuntimeConfig:
    for name in CONFIG_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "m0")
    monkeypatch.setenv("PROVIDER", "fake")
    return RuntimeConfig.from_env()


def test_m0_allows_only_condition_a(monkeypatch: pytest.MonkeyPatch) -> None:
    config = make_m0_config(monkeypatch)

    assert config.allowed_conditions() == ["A"]
    config.assert_condition(" a ")

    for condition in ("B", "C", "C-P", "C-N", "C-O"):
        with pytest.raises(ValueError, match=f"not available in profile m0"):
            config.assert_condition(condition)


def test_unknown_condition_is_rejected_without_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    config = make_m0_config(monkeypatch)

    with pytest.raises(ValueError, match="Unknown condition Z"):
        config.assert_condition("z")


def test_condition_table_keeps_m0_a_vanilla_and_feature_off() -> None:
    conditions_path = Path(__file__).parents[1] / "config" / "conditions.json"
    table = json.loads(conditions_path.read_text(encoding="utf-8"))

    assert set(CONDITION_DEFINITIONS) == set(table)
    assert table["A"]["description"] == "Vanilla RAG"
    assert {table["A"][flag] for flag in ("P", "N", "O")} == {False}


def test_public_config_is_allowlisted_and_hash_is_deterministic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = make_m0_config(monkeypatch)
    public = config.public_dict()

    assert set(public) == {
        "implementation_profile",
        "provider",
        "local_model",
        "task_top_k",
        "planning_top_k",
        "max_context_tokens",
        "max_output_tokens",
        "max_run_tokens",
        "retry_limit",
        "retrieval_min_score",
        "retrieval_mode",
        "vector_backend",
        "local_embedding_model",
    }
    assert "config_hash" not in public
    assert config.config_hash() == config.config_hash()
    assert len(config.config_hash()) == 16
    assert all(character in "0123456789abcdef" for character in config.config_hash())


def test_public_config_change_changes_hash(monkeypatch: pytest.MonkeyPatch) -> None:
    config = make_m0_config(monkeypatch)
    original_hash = config.config_hash()

    monkeypatch.setenv("MAX_CONTEXT_TOKENS", "4000")
    changed = RuntimeConfig.from_env()

    assert changed.public_dict()["max_context_tokens"] == 4000
    assert changed.config_hash() != original_hash
