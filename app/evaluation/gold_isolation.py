"""Static guard: runtime-generation modules must not import gold assets."""
from __future__ import annotations

from pathlib import Path


GENERATION_MODULES = (
    "app/research/pipeline.py",
    "app/research/decomposer.py",
    "app/research/worker.py",
    "app/research/synthesizer.py",
    "app/research/planning_retrieval.py",
    "app/providers/ollama.py",
)
FORBIDDEN_GOLD_MARKERS = ("gold-approval-packet", "gold-template.csv", "gold_obligation", "relevant_evidence_ids")


def verify_gold_isolation(project_root: Path) -> dict[str, object]:
    """Return a deterministic static result without reading any gold values."""

    violations: list[dict[str, object]] = []
    inspected: list[str] = []
    for relative in GENERATION_MODULES:
        path = project_root / relative
        inspected.append(relative)
        text = path.read_text(encoding="utf-8")
        for marker in FORBIDDEN_GOLD_MARKERS:
            if marker in text:
                violations.append({"path": relative, "marker": marker})
    return {
        "decision": "PASS" if not violations else "FAIL",
        "inspected_generation_modules": inspected,
        "forbidden_markers": list(FORBIDDEN_GOLD_MARKERS),
        "violations": violations,
        "scope_limit": "Static source guard only; it cannot prove properties of future external data.",
    }
