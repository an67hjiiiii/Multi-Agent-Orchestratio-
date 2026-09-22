from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Literal, TypeAlias


Status: TypeAlias = Literal["COMPLETE", "PARTIAL", "NO_EVIDENCE", "FAILED"]

@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

@dataclass
class ProviderResult:
    text: str
    usage: Usage = field(default_factory=Usage)
    request_id: str = ""
    model: str = ""

@dataclass
class SourceChunk:
    chunk_id: str
    source_id: str
    source_name: str
    text: str
    index: int
    score: float = 0.0
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Citation:
    """A validated locator, kept separate from the evidence it points to."""

    locator: str

    def __post_init__(self) -> None:
        if not isinstance(self.locator, str) or not self.locator.strip():
            raise ValueError("citation locator must be a non-empty string")

    def to_value(self) -> str:
        return self.locator

@dataclass
class Task:
    task_id: str
    goal: str
    domain: str = "api_architecture"
    depends_on: list[str] = field(default_factory=list)
    evidence_needs: list[str] = field(default_factory=list)
    object: str = ""
    action: str = ""
    deliverable: str = ""
    requirement_ids: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    # Planning metadata is additive. Existing runtime callers can continue
    # to use goal/object/domain while the adapter preserves the richer plan.
    title: str = ""
    expected_output: str = ""
    role_profile: str = ""
    covers_obligations: list[str] = field(default_factory=list)

@dataclass
class TaskResult:
    task_id: str
    domain: str
    status: str
    answer: str
    evidence_ids: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    invalid_citations: list[str] = field(default_factory=list)
    missing_information: list[str] = field(default_factory=list)
    status_reason: str = ""

@dataclass
class RunMetrics:
    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    context_tokens_est: int = 0
    context_chars: int = 0
    retrieved_chunks: int = 0
    selected_chunks: int = 0
    dropped_chunks: int = 0
    duplicate_tasks_removed: int = 0
    citations_emitted: int = 0
    citations_valid: int = 0
    retrieval_latency_ms: int = 0
    generation_latency_ms: int = 0
    latency_ms: int = 0
    peak_rss_mb: float | None = None
    gpu_memory_mb: float | None = None

    def add_usage(self, usage: Usage) -> None:
        self.llm_calls += 1
        self.input_tokens += usage.input_tokens
        self.output_tokens += usage.output_tokens

    def add_citations(self, valid: list[str], invalid: list[str]) -> None:
        self.citations_valid += len(valid)
        self.citations_emitted += len(valid) + len(invalid)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["total_tokens"] = self.input_tokens + self.output_tokens
        d["citation_locator_validity"] = (
            round(self.citations_valid / self.citations_emitted, 4)
            if self.citations_emitted else None
        )
        return d


# SourceChunk is the existing canonical evidence payload. The alias makes
# that boundary explicit without introducing a second runtime representation.
Evidence = SourceChunk
