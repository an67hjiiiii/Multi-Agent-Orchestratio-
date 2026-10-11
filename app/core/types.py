from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any

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

@dataclass
class Task:
    task_id: str
    goal: str
    domain: str = "api_architecture"
    depends_on: list[str] = field(default_factory=list)
    evidence_needs: list[str] = field(default_factory=list)

@dataclass
class Obligation:
    """A distinct user requirement that the plan must preserve."""

    obligation_id: str
    description: str
    required: bool = True

@dataclass
class Concern:
    """A review concern recorded separately from a required obligation."""

    concern_id: str
    description: str
    domain: str = "general"

@dataclass
class TaskPlan:
    """Structured plan that keeps requirements, concerns, and tasks distinct."""

    request: str
    obligations: list[Obligation] = field(default_factory=list)
    concerns: list[Concern] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)

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
