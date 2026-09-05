from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
CONDITIONS_PATH: Final[Path] = ROOT / "config" / "conditions.json"
load_dotenv(ROOT / ".env", override=False)

CONDITION_FLAGS: Final[tuple[str, ...]] = ("P", "N", "O")


def _load_condition_definitions() -> dict[str, dict[str, object]]:
    """Load and validate the machine-readable condition table."""

    try:
        raw = json.loads(CONDITIONS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Unable to load condition config: {CONDITIONS_PATH}") from exc

    if not isinstance(raw, dict) or not raw:
        raise ValueError("Condition config must be a non-empty JSON object")

    definitions: dict[str, dict[str, object]] = {}
    for raw_condition, raw_definition in raw.items():
        if not isinstance(raw_condition, str):
            raise ValueError("Condition IDs must be strings")
        condition = raw_condition.strip().upper()
        if not condition or condition != raw_condition or condition in definitions:
            raise ValueError(f"Invalid or duplicate condition ID: {raw_condition!r}")
        if not isinstance(raw_definition, dict):
            raise ValueError(f"Condition {condition} must be a JSON object")

        description = raw_definition.get("description")
        if not isinstance(description, str) or not description.strip():
            raise ValueError(f"Condition {condition} requires a description")

        definition = dict(raw_definition)
        definition["description"] = description.strip()
        for flag in CONDITION_FLAGS:
            if not isinstance(definition.get(flag), bool):
                raise ValueError(f"Condition {condition} flag {flag} must be boolean")
        definitions[condition] = definition

    if "A" not in definitions:
        raise ValueError("Condition config must define M0 condition A")
    if any(definitions["A"][flag] for flag in CONDITION_FLAGS):
        raise ValueError("M0 condition A must keep P, N, and O disabled")
    return definitions


CONDITION_DEFINITIONS: Final[dict[str, dict[str, object]]] = _load_condition_definitions()

PROFILE_CONDITIONS: Final[dict[str, frozenset[str]]] = {
    "m0": frozenset({"A"}),
    "m1": frozenset({"A", "B", "C"}),
    "m2": frozenset({"A", "B", "C", "C-P", "C-N", "C-O"}),
    # Engineering-only profile used to test future wiring before a milestone is claimed.
    "dev": frozenset({"A", "B", "C", "C-P", "C-N", "C-O"}),
}

for profile, conditions in PROFILE_CONDITIONS.items():
    unknown = conditions.difference(CONDITION_DEFINITIONS)
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ValueError(f"Profile {profile} references unknown condition(s): {names}")


PUBLIC_CONFIG_FIELDS: Final[tuple[str, ...]] = (
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
)


def _normalize_condition(condition: str) -> str:
    if not isinstance(condition, str):
        raise ValueError("Condition must be a string")
    normalized = condition.strip().upper()
    if not normalized:
        raise ValueError("Condition is required")
    return normalized


@dataclass(frozen=True)
class RuntimeConfig:
    implementation_profile: str
    provider: str
    local_model: str
    task_top_k: int
    planning_top_k: int
    max_context_tokens: int
    max_output_tokens: int
    max_run_tokens: int
    retry_limit: int
    retrieval_min_score: float

    @classmethod
    def from_env(cls) -> "RuntimeConfig":
        profile = os.getenv("IMPLEMENTATION_PROFILE", "m0").strip().lower()
        if profile not in PROFILE_CONDITIONS:
            raise ValueError(f"Unsupported IMPLEMENTATION_PROFILE={profile}")
        return cls(
            implementation_profile=profile,
            provider=os.getenv("PROVIDER", "fake").strip().lower(),
            local_model=os.getenv("LOCAL_LLM_MODEL", "qwen3:4b").strip(),
            task_top_k=max(1, int(os.getenv("TASK_TOP_K", "6"))),
            planning_top_k=max(1, int(os.getenv("PLANNING_TOP_K", "3"))),
            max_context_tokens=max(256, int(os.getenv("MAX_CONTEXT_TOKENS", "3000"))),
            max_output_tokens=max(64, int(os.getenv("MAX_OUTPUT_TOKENS", "700"))),
            max_run_tokens=max(512, int(os.getenv("MAX_RUN_TOKENS", "12000"))),
            retry_limit=max(0, int(os.getenv("RETRY_LIMIT", "1"))),
            retrieval_min_score=max(0.0, float(os.getenv("MIN_RETRIEVAL_SCORE", "0.18"))),
        )

    def allowed_conditions(self) -> list[str]:
        return sorted(PROFILE_CONDITIONS[self.implementation_profile])

    def assert_condition(self, condition: str) -> None:
        normalized = _normalize_condition(condition)
        if normalized not in CONDITION_DEFINITIONS:
            raise ValueError(f"Unknown condition {normalized}")
        if normalized not in PROFILE_CONDITIONS[self.implementation_profile]:
            allowed = ", ".join(self.allowed_conditions())
            raise ValueError(
                f"Condition {normalized} is not available in profile {self.implementation_profile}. "
                f"Allowed: {allowed}"
            )

    def public_dict(self) -> dict[str, object]:
        """Return the allowlisted, JSON-serializable runtime configuration."""

        return {field: getattr(self, field) for field in PUBLIC_CONFIG_FIELDS}

    def config_hash(self) -> str:
        """Return a stable short SHA-256 over the public configuration only."""

        payload = json.dumps(self.public_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
