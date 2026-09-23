from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import os
import re
import sys
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any, Iterator

_ROOT_FOR_IMPORT = Path(__file__).resolve().parents[1]
if str(_ROOT_FOR_IMPORT) not in sys.path:
    sys.path.insert(0, str(_ROOT_FOR_IMPORT))

from app.research.runtime_factory import build_research_pipeline, prepare_source_store
from app.storage.source_store import SourceStore


ROOT = _ROOT_FOR_IMPORT
DEFAULT_CASES_PATH = ROOT / "datasets" / "calibration" / "m0_cases.json"
DEFAULT_CORPUS_DIR = ROOT / "datasets" / "domain"
DEFAULT_DATA_DIR = ROOT / "data" / "m0_calibration"
DEFAULT_RUNS_DIR = ROOT / "runs" / "m0_calibration"
DEFAULT_OUTPUT_DIR = ROOT / "reports" / "calibration"

EXPECTED_CASE_IDS = tuple(f"M0-{index:02d}" for index in range(1, 13))
EXPECTED_CASE_COUNT = len(EXPECTED_CASE_IDS)
EXPECTED_EVIDENCE = {"present", "missing"}

# Keep this order stable so a report can be diffed without depending on dict
# insertion order or the fields returned by a particular provider.
REPORT_FIELDS = (
    "case_id",
    "query",
    "expected_evidence",
    "expected_source",
    "status",
    "answer",
    "model",
    "citations",
    "citation_sources",
    "citation_count",
    "invalid_citation_count",
    "citation_locator_validity",
    "locator_valid",
    "evidence_behavior_ok",
    "status_behavior_ok",
    "source_match",
    "condition_ok",
    "profile_ok",
    "automated_pass",
    "llm_calls",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "retrieval_latency_ms",
    "generation_latency_ms",
    "e2e_latency_ms",
    "peak_rss_mb",
    "gpu_memory_mb",
    "implementation_profile",
    "config_hash",
    "corpus_snapshot",
    "run_id",
    "failure_type",
    "manual_correctness",
    "manual_correctness_reason",
    "manual_faithfulness",
    "manual_faithfulness_reason",
)


def _as_path(path: str | Path) -> Path:
    return path if isinstance(path, Path) else Path(path)


def sha256_file(path: str | Path) -> str:
    """Return the content hash used to identify the exact calibration input."""

    digest = hashlib.sha256()
    with _as_path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_cases(cases: Any) -> None:
    """Validate the locked M0 case manifest without changing its gold data."""

    if not isinstance(cases, list):
        raise ValueError("M0 calibration manifest must be a JSON array")
    if len(cases) != EXPECTED_CASE_COUNT:
        raise ValueError(
            f"M0 calibration requires exactly {EXPECTED_CASE_COUNT} cases; got {len(cases)}"
        )

    case_ids: list[str] = []
    for index, case in enumerate(cases, start=1):
        if not isinstance(case, dict):
            raise ValueError(f"M0 calibration case {index} must be an object")
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError(f"M0 calibration case {index} must have a non-empty id")
        case_ids.append(case_id)

        query = case.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError(f"M0 calibration case {case_id} must have a non-empty query")

        expected_evidence = case.get("expected_evidence")
        if expected_evidence not in EXPECTED_EVIDENCE:
            raise ValueError(
                f"M0 calibration case {case_id} expected_evidence must be present or missing"
            )

        expected_source = case.get("expected_source")
        if expected_evidence == "present":
            if not isinstance(expected_source, str) or not expected_source.strip():
                raise ValueError(
                    f"M0 calibration case {case_id} with present evidence needs expected_source"
                )
        elif expected_source not in (None, ""):
            raise ValueError(
                f"M0 calibration case {case_id} with missing evidence cannot have expected_source"
            )

    if len(set(case_ids)) != len(case_ids):
        raise ValueError("M0 calibration case ids must be unique")
    if tuple(case_ids) != EXPECTED_CASE_IDS:
        raise ValueError(
            "M0 calibration case order/ids must be " + ", ".join(EXPECTED_CASE_IDS)
        )


def load_cases(path: str | Path = DEFAULT_CASES_PATH) -> list[dict[str, Any]]:
    """Load and validate the immutable 12-case M0 calibration manifest."""

    case_path = _as_path(path)
    try:
        cases = json.loads(case_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not load M0 calibration manifest {case_path}: {exc}") from exc
    validate_cases(cases)
    return cases


def prepare_store(
    data_dir: str | Path = DEFAULT_DATA_DIR,
    corpus_dir: str | Path = DEFAULT_CORPUS_DIR,
) -> SourceStore:
    """Compatibility wrapper for the shared application composition seam."""

    return prepare_source_store(data_dir=data_dir, corpus_dir=corpus_dir)


def _ordered_unique(values: list[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            result.append(text)
            seen.add(text)
    return result


def _list_value(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _numeric(value: Any) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def _failure_type(run: dict[str, Any]) -> str:
    events = run.get("events") or []
    for event in reversed(events if isinstance(events, list) else []):
        if isinstance(event, dict) and event.get("stage") in {"run_failed", "runner_failed"}:
            return str(event.get("error_type") or "FAILED")
    return "" if run.get("status") != "FAILED" else "FAILED"


def build_case_row(
    case: dict[str, Any],
    run: dict[str, Any],
    store: SourceStore,
) -> dict[str, Any]:
    """Convert one pipeline run to a stable, non-semantic calibration row."""

    task_results = run.get("task_results") or []
    citation_values: list[Any] = []
    invalid_values: list[Any] = []
    for result in task_results if isinstance(task_results, list) else []:
        if not isinstance(result, dict):
            continue
        citation_values.extend(_list_value(result.get("citations")))
        invalid_values.extend(_list_value(result.get("invalid_citations")))

    citations = _ordered_unique(citation_values)
    invalid_citations = _ordered_unique(invalid_values)
    citation_sources = _ordered_unique(
        [
            chunk["source_name"]
            for citation in citations
            if (chunk := store.chunk(citation)) is not None
        ]
    )

    metrics = run.get("metrics") or {}
    if not isinstance(metrics, dict):
        metrics = {}
    status = str(run.get("status") or "FAILED").upper()
    expected_evidence = case["expected_evidence"]
    evidence_present = bool(citations)
    locator_ratio = metrics.get("citation_locator_validity")

    # A null ratio is valid only when no citation was emitted. A present case
    # must have an actual 1.0 locator result; otherwise the report must expose
    # the structural failure instead of treating missing telemetry as success.
    if evidence_present:
        locator_valid = locator_ratio in (1, 1.0) and all(
            store.chunk(citation) is not None for citation in citations
        )
    else:
        locator_valid = locator_ratio in (None, 1, 1.0) and not invalid_citations

    evidence_behavior_ok = evidence_present if expected_evidence == "present" else not evidence_present
    status_behavior_ok = (
        status in {"COMPLETE", "PARTIAL"}
        if expected_evidence == "present"
        else status == "NO_EVIDENCE"
    )
    expected_source = case.get("expected_source") or ""
    source_match = not expected_source or expected_source in citation_sources
    condition_ok = run.get("condition") == "A"
    profile_ok = run.get("implementation_profile") == "m0"
    automated_pass = all(
        (
            evidence_behavior_ok,
            status_behavior_ok,
            locator_valid,
            not invalid_citations,
            source_match,
            condition_ok,
            profile_ok,
        )
    )

    input_tokens = _numeric(metrics.get("input_tokens")) or 0
    output_tokens = _numeric(metrics.get("output_tokens")) or 0
    total_tokens = _numeric(metrics.get("total_tokens"))
    if total_tokens is None:
        total_tokens = input_tokens + output_tokens

    return {
        "case_id": case["id"],
        "query": case["query"],
        "expected_evidence": expected_evidence,
        "expected_source": expected_source,
        "status": status,
        "answer": str(run.get("answer") or ""),
        "model": str(run.get("model") or ""),
        "citations": ";".join(citations),
        "citation_sources": ";".join(citation_sources),
        "citation_count": len(citations),
        "invalid_citation_count": len(invalid_citations),
        "citation_locator_validity": locator_ratio,
        "locator_valid": locator_valid,
        "evidence_behavior_ok": evidence_behavior_ok,
        "status_behavior_ok": status_behavior_ok,
        "source_match": source_match,
        "condition_ok": condition_ok,
        "profile_ok": profile_ok,
        "automated_pass": automated_pass,
        "llm_calls": metrics.get("llm_calls", 0),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "retrieval_latency_ms": metrics.get("retrieval_latency_ms"),
        "generation_latency_ms": metrics.get("generation_latency_ms"),
        "e2e_latency_ms": metrics.get("latency_ms"),
        "peak_rss_mb": metrics.get("peak_rss_mb"),
        "gpu_memory_mb": metrics.get("gpu_memory_mb"),
        "implementation_profile": str(run.get("implementation_profile") or ""),
        "config_hash": str(run.get("config_hash") or ""),
        "corpus_snapshot": str(run.get("source_snapshot_id") or ""),
        "run_id": str(run.get("run_id") or ""),
        "failure_type": _failure_type(run),
        "manual_correctness": "UNSCORED",
        "manual_correctness_reason": "",
        "manual_faithfulness": "UNSCORED",
        "manual_faithfulness_reason": "",
    }


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return round(ordered[lower] + (ordered[upper] - ordered[lower]) * fraction, 2)


def _metric_summary(rows: list[dict[str, Any]], key: str) -> dict[str, int | float | None]:
    values = [
        float(value)
        for row in rows
        if (value := _numeric(row.get(key))) is not None
    ]
    return {
        "count": len(values),
        "median": round(median(values), 2) if values else None,
        "p95": _percentile(values, 0.95),
        "max": round(max(values), 2) if values else None,
    }


def _score_counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row.get(key) or "UNSCORED") for row in rows).items()))


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Build deterministic aggregate checks; these are not semantic scores."""

    status_counts = dict(sorted(Counter(str(row.get("status") or "FAILED") for row in rows).items()))
    count = len(rows)
    automated_pass_count = sum(bool(row.get("automated_pass")) for row in rows)
    return {
        "case_count": count,
        "attempted_cases": count,
        "automated_pass_count": automated_pass_count,
        "automated_pass_rate": round(automated_pass_count / count, 4) if count else 0.0,
        "evidence_behavior_pass_count": sum(bool(row.get("evidence_behavior_ok")) for row in rows),
        "locator_valid_count": sum(bool(row.get("locator_valid")) for row in rows),
        "source_match_count": sum(bool(row.get("source_match")) for row in rows),
        "status_counts": status_counts,
        "failed_cases": status_counts.get("FAILED", 0),
        "manual_correctness": _score_counts(rows, "manual_correctness"),
        "manual_faithfulness": _score_counts(rows, "manual_faithfulness"),
        "e2e_latency_ms": _metric_summary(rows, "e2e_latency_ms"),
        "retrieval_latency_ms": _metric_summary(rows, "retrieval_latency_ms"),
        "total_tokens": sum(float(_numeric(row.get("total_tokens")) or 0) for row in rows),
        "peak_rss_mb": max(
            (float(value) for row in rows if (value := _numeric(row.get("peak_rss_mb"))) is not None),
            default=None,
        ),
        "peak_gpu_memory_mb": max(
            (float(value) for row in rows if (value := _numeric(row.get("gpu_memory_mb"))) is not None),
            default=None,
        ),
        "semantic_evidence": "NOT_ESTABLISHED",
        "manual_review_required": True,
    }


def _relative_to_root(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def build_report(
    cases: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    *,
    provider: str,
    cases_path: str | Path,
    corpus_snapshot: str,
    generated_at: str,
) -> dict[str, Any]:
    """Create the JSON report envelope with stable metadata and row order."""

    models = sorted({row["model"] for row in rows if row.get("model")})
    config_hashes = sorted({row["config_hash"] for row in rows if row.get("config_hash")})
    profiles = sorted({row["implementation_profile"] for row in rows if row.get("implementation_profile")})
    observed_snapshots = sorted({row["corpus_snapshot"] for row in rows if row.get("corpus_snapshot")})
    case_path = _as_path(cases_path)
    return {
        "report_schema": "m0-calibration-v2",
        "generated_at": generated_at,
        "milestone": "M0",
        "condition": "A",
        "provider": provider,
        "implementation_profile": "m0",
        "model": models[0] if len(models) == 1 else None,
        "config_hash": config_hashes[0] if len(config_hashes) == 1 else None,
        "corpus_snapshot": corpus_snapshot,
        "runtime": {
            "observed_models": models,
            "observed_config_hashes": config_hashes,
            "observed_profiles": profiles,
            "observed_corpus_snapshots": observed_snapshots,
        },
        "dataset": {
            "path": _relative_to_root(case_path),
            "sha256": sha256_file(case_path),
            "case_count": len(cases),
            "case_ids": [case["id"] for case in cases],
        },
        "summary": summarize_rows(rows),
        "evidence_boundary": (
            "Automated rows validate wiring, status, citation locator structure, and expected source mapping. "
            "They do not establish semantic correctness or faithfulness."
        ),
        "rows": rows,
    }


def _safe_stamp(stamp: str | None) -> str:
    value = stamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise ValueError("stamp may contain only letters, numbers, underscore, and hyphen")
    return value


def write_reports(
    report: dict[str, Any],
    *,
    output_dir: str | Path,
    provider: str,
    stamp: str | None = None,
) -> tuple[Path, Path]:
    """Write JSON and CSV using stable field ordering and case ordering."""

    out_dir = _as_path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_stamp = _safe_stamp(stamp)
    json_path = out_dir / f"m0_calibration_{provider}_{safe_stamp}.json"
    csv_path = out_dir / f"m0_calibration_{provider}_{safe_stamp}.csv"

    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    rows = report.get("rows") or []
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REPORT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in REPORT_FIELDS})
    return json_path, csv_path


def _runner_failure(case: dict[str, Any], provider: str, exc: Exception) -> dict[str, Any]:
    """Represent an unexpected case-level exception without copying raw bodies."""

    return {
        "run_id": "",
        "condition": "A",
        "implementation_profile": "m0",
        "provider": provider,
        "model": os.getenv("LOCAL_LLM_MODEL", "qwen3:4b"),
        "query": case["query"],
        "status": "FAILED",
        "answer": "",
        "task_results": [],
        "metrics": {},
        "events": [{"stage": "runner_failed", "error_type": type(exc).__name__}],
    }


@contextmanager
def _runtime_environment(provider: str) -> Iterator[None]:
    previous = {
        key: os.environ.get(key)
        for key in ("IMPLEMENTATION_PROFILE", "PROVIDER")
    }
    os.environ["IMPLEMENTATION_PROFILE"] = "m0"
    os.environ["PROVIDER"] = provider
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


async def run_calibration(
    *,
    provider: str = "fake",
    cases_path: str | Path = DEFAULT_CASES_PATH,
    corpus_dir: str | Path = DEFAULT_CORPUS_DIR,
    data_dir: str | Path = DEFAULT_DATA_DIR,
    runs_dir: str | Path = DEFAULT_RUNS_DIR,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    stamp: str | None = None,
    emit_progress: bool = False,
) -> dict[str, Any]:
    """Run all cases serially and return the report plus output paths."""

    selected_provider = str(provider).strip().lower()
    if selected_provider not in {"fake", "ollama"}:
        raise ValueError("provider must be fake or ollama")

    cases = load_cases(cases_path)
    store = prepare_store(data_dir=data_dir, corpus_dir=corpus_dir)
    expected_sources = {
        case["expected_source"]
        for case in cases
        if case.get("expected_source")
    }
    available_sources = {source["source_name"] for source in store.list_sources()}
    missing_sources = sorted(expected_sources - available_sources)
    if missing_sources:
        raise ValueError(
            "Calibration cases reference sources absent from the corpus: "
            + ", ".join(missing_sources)
        )

    rows: list[dict[str, Any]] = []
    with _runtime_environment(selected_provider):
        pipeline = build_research_pipeline(store, _as_path(runs_dir))
        for case in cases:
            try:
                run = await pipeline.run(case["query"], "A", selected_provider)
            except Exception as exc:  # Keep the 12-row report complete and explicit.
                run = _runner_failure(case, selected_provider, exc)
            row = build_case_row(case, run, store)
            rows.append(row)
            if emit_progress:
                print(
                    case["id"],
                    row["status"],
                    "automated_pass=" + str(row["automated_pass"]),
                    row["e2e_latency_ms"],
                    "ms",
                )

    generated_at = datetime.now(timezone.utc).isoformat()
    report = build_report(
        cases,
        rows,
        provider=selected_provider,
        cases_path=cases_path,
        corpus_snapshot=store.snapshot_id(),
        generated_at=generated_at,
    )
    json_path, csv_path = write_reports(
        report,
        output_dir=output_dir,
        provider=selected_provider,
        stamp=stamp,
    )
    return {
        "report": report,
        "json_path": json_path,
        "csv_path": csv_path,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the serial M0 calibration set.")
    parser.add_argument(
        "--provider",
        choices=["fake", "ollama"],
        default=os.getenv("PROVIDER", "fake").strip().lower(),
        help="fake for wiring tests; ollama only for the target-laptop local gate",
    )
    parser.add_argument("--cases-path", type=Path, default=DEFAULT_CASES_PATH)
    parser.add_argument("--corpus-dir", type=Path, default=DEFAULT_CORPUS_DIR)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--stamp",
        help="Optional safe filename stamp; useful for deterministic report paths in tests",
    )
    return parser


async def main(argv: list[str] | None = None) -> dict[str, Any]:
    args = build_parser().parse_args(argv)
    result = await run_calibration(
        provider=args.provider,
        cases_path=args.cases_path,
        corpus_dir=args.corpus_dir,
        data_dir=args.data_dir,
        runs_dir=args.runs_dir,
        output_dir=args.output_dir,
        stamp=args.stamp,
        emit_progress=True,
    )
    print(
        {
            "json": str(result["json_path"]),
            "csv": str(result["csv_path"]),
            "cases": result["report"]["summary"]["case_count"],
            "automated_pass": result["report"]["summary"]["automated_pass_count"],
        }
    )
    return result


if __name__ == "__main__":
    asyncio.run(main())
