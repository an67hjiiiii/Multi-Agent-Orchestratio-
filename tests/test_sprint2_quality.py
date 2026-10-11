"""Focused Sprint 2 QA checks for the fixed M0 candidate seam.

These checks are contract and artifact checks only.  They do not run Ollama,
change the calibration set, or claim semantic correctness.  The test names
map directly to the scoped MAI and CHUNG ownership IDs in the Sprint 2 QA
handoff.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.core.citations import validate_citations
from app.core.types import ProviderResult, RunMetrics, SourceChunk, Usage
from app.providers.fake import FakeProvider
from app.research.pipeline import ResearchPipeline
from app.research.vanilla import answer_vanilla
from app.retrieval.text import make_chunks, retrieve
from app.storage.run_store import RunStore
from app.storage.source_store import SourceStore


ROOT = Path(__file__).resolve().parents[1]
CALIBRATION_CASES = ROOT / "datasets" / "calibration" / "m0_cases.json"
FIXED_FAKE_REPORT = (
    ROOT / "reports" / "calibration" / "m0_calibration_fake_20260905T105713Z.json"
)


def test_s2_mai_01_chunk_ids_preserve_integrity_and_provenance() -> None:
    """S2-MAI-01: normalized source bytes map to stable, scoped chunk IDs."""

    first = make_chunks("security.md", "Alpha\r\n\r\nBeta", max_chars=6)
    equivalent = make_chunks("security.md", "Alpha\n\nBeta", max_chars=6)
    other_source = make_chunks("database.md", "Alpha\n\nBeta", max_chars=6)

    assert [chunk.chunk_id for chunk in first] == [
        chunk.chunk_id for chunk in equivalent
    ]
    assert [chunk.source_id for chunk in first] == [
        chunk.source_id for chunk in equivalent
    ]
    assert [chunk.index for chunk in first] == [0, 1]
    assert first[0].source_id != other_source[0].source_id
    assert first[0].chunk_id != other_source[0].chunk_id
    assert all(chunk.chunk_id.startswith(f"{chunk.source_id}_c") for chunk in first)


def test_s2_mai_02_pipeline_trace_keeps_source_and_chunk_provenance(tmp_path, monkeypatch) -> None:
    """S2-MAI-02: retrieval IDs, source snapshot, and citations remain linkable."""

    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "m0")
    source_store = SourceStore(str(tmp_path / "data"))
    imported = source_store.import_text(
        "api.md", "API contracts define request validation and error responses."
    )
    run_store = RunStore(str(tmp_path / "runs"))

    run = asyncio.run(
        ResearchPipeline(source_store, run_store).run(
            "What do API contracts define?", "A", "fake"
        )
    )

    retrieval_event = next(
        event for event in run["events"] if event["stage"] == "vanilla_retrieval"
    )
    evidence_ids = run["task_results"][0]["evidence_ids"]
    citations = run["task_results"][0]["citations"]
    persisted_chunks = {chunk.chunk_id: chunk for chunk in source_store.chunks()}

    assert run["source_snapshot_id"] == imported["snapshot_id"]
    assert run["source_snapshot_id"].startswith("corpus_")
    assert run["effective_config"]["condition"] == "A"
    assert run["effective_config"]["implementation_profile"] == "m0"
    assert run["config_hash"]
    assert set(retrieval_event["selected"]) == set(evidence_ids)
    assert set(evidence_ids) <= set(persisted_chunks)
    assert set(citations) <= set(evidence_ids)
    assert all(persisted_chunks[cid].source_name == "api.md" for cid in evidence_ids)
    assert run_store.get(run["run_id"]) == run


def test_s2_mai_03_retrieval_relevance_prefers_matching_fixed_source() -> None:
    """S2-MAI-03: lexical retrieval selects matching evidence and leaves gaps empty."""

    chunks = [
        *make_chunks(
            "security.md",
            "Authentication verifies identity. Authorization checks permissions server-side.",
        ),
        *make_chunks(
            "database.md",
            "Queries for frequent identifiers should be reviewed for indexes.",
        ),
    ]

    security_hits = retrieve(
        "What does server-side authorization check?", chunks, top_k=2, min_score=0.18
    )
    missing_hits = retrieve(
        "What is the production deployment region?", chunks, top_k=2, min_score=0.18
    )

    assert security_hits
    assert security_hits[0].source_name == "security.md"
    assert security_hits[0].score > 0
    assert missing_hits == []


class _InvalidCitationProvider:
    name = "invalid-citation-test"
    model = "contract-test"

    async def generate(self, *, system: str, user: str) -> ProviderResult:
        del system, user
        return ProviderResult(
            text=json.dumps(
                {
                    "status": "COMPLETE",
                    "answer": "Grounded claim",
                    "citations": [
                        "src_0123456789abcdef_c0000",
                        "src_missing00000000_c0000",
                        "src_0123456789abcdef_c0000",
                    ],
                    "missing_information": [],
                }
            ),
            usage=Usage(input_tokens=10, output_tokens=5),
        )


def test_s2_mai_04_invalid_citations_are_removed_and_downgraded() -> None:
    """S2-MAI-04: citation validation is locator-level, duplicate-safe, and explicit."""

    valid_id = "src_0123456789abcdef_c0000"
    evidence = [
        SourceChunk(
            chunk_id=valid_id,
            source_id="src_0123456789abcdef",
            source_name="security.md",
            text="Authentication verifies identity.",
            index=0,
        )
    ]
    direct_valid, direct_invalid = validate_citations(
        [valid_id, "src_missing00000000_c0000", valid_id], evidence
    )
    metrics = RunMetrics()
    result = asyncio.run(
        answer_vanilla(_InvalidCitationProvider(), "What is verified?", evidence, metrics)
    )

    assert direct_valid == [valid_id]
    assert direct_invalid == ["src_missing00000000_c0000"]
    assert result.status == "PARTIAL"
    assert result.citations == [valid_id]
    assert result.invalid_citations == ["src_missing00000000_c0000"]
    assert "invalid citation locator(s) removed" in result.missing_information
    assert f"[{valid_id}]" in result.answer
    assert "src_missing00000000_c0000" not in result.answer
    assert metrics.to_dict()["citation_locator_validity"] == 0.5


def test_s2_mai_06_fixed_calibration_artifact_matches_approved_case_shape() -> None:
    """S2-MAI-06/S2-CHUNG-03: fixed calibration evidence is internally consistent."""

    cases = json.loads(CALIBRATION_CASES.read_text(encoding="utf-8"))
    report = json.loads(FIXED_FAKE_REPORT.read_text(encoding="utf-8"))
    rows = report["rows"]
    cases_by_id = {case["id"]: case for case in cases}
    rows_by_id = {row["case_id"]: row for row in rows}

    assert report["provider"] == "fake"
    assert len(cases) == len(rows) == 12
    assert len(cases_by_id) == len(cases)
    assert set(cases_by_id) == set(rows_by_id)
    assert sum(case["expected_evidence"] == "present" for case in cases) == 9
    assert sum(case["expected_evidence"] == "missing" for case in cases) == 3

    for case_id, case in cases_by_id.items():
        row = rows_by_id[case_id]
        assert row["expected_evidence"] == case["expected_evidence"]
        assert row["expected_source"] == (case["expected_source"] or "")
        assert row["locator_valid"] is True
        assert row["evidence_behavior_ok"] is True
        assert row["source_match"] is True
        assert row["manual_correctness"] == "UNSCORED"
        assert row["manual_faithfulness"] == "UNSCORED"
