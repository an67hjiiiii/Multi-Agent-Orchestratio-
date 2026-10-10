from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from dataclasses import dataclass, asdict

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env", override=False)

PROFILE_CONDITIONS = {
    "m0": {"A"},
    "m1": {"A", "B", "C"},
    "m2": {"A", "B", "C", "C-P", "C-N", "C-O"},
    # Engineering-only profile used to test future wiring before a milestone is claimed.
    "dev": {"A", "B", "C", "C-P", "C-N", "C-O"},
}

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
        if condition not in PROFILE_CONDITIONS[self.implementation_profile]:
            allowed = ", ".join(self.allowed_conditions())
            raise ValueError(
                f"Condition {condition} is not available in profile {self.implementation_profile}. "
                f"Allowed: {allowed}"
            )

    def public_dict(self) -> dict:
        return asdict(self)

    def config_hash(self) -> str:
        payload = json.dumps(self.public_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
