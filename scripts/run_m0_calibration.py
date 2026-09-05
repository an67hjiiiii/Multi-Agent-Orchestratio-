from __future__ import annotations
import sys
from pathlib import Path as _Path
_ROOT_FOR_IMPORT = _Path(__file__).resolve().parents[1]
if str(_ROOT_FOR_IMPORT) not in sys.path:
    sys.path.insert(0, str(_ROOT_FOR_IMPORT))
import argparse
import asyncio
import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("IMPLEMENTATION_PROFILE", "m0")

from app.research.pipeline import ResearchPipeline
from app.storage.source_store import SourceStore
from app.storage.run_store import RunStore


def load_cases() -> list[dict]:
    return json.loads((ROOT / "datasets" / "calibration" / "m0_cases.json").read_text(encoding="utf-8"))


def prepare_store() -> SourceStore:
    root = ROOT / "data" / "m0_calibration"
    store = SourceStore(str(root))
    store.clear()
    for p in sorted((ROOT / "datasets" / "domain").glob("*.md")):
        store.import_text(p.name, p.read_text(encoding="utf-8"))
    return store


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", choices=["fake", "ollama"], default=os.getenv("PROVIDER", "fake"))
    args = ap.parse_args()
    os.environ["PROVIDER"] = args.provider
    os.environ["IMPLEMENTATION_PROFILE"] = "m0"

    store = prepare_store()
    run_root = ROOT / "runs" / "m0_calibration"
    pipe = ResearchPipeline(store, RunStore(str(run_root)))
    rows: list[dict] = []
    for case in load_cases():
        run = await pipe.run(case["query"], "A", args.provider)
        citations = [c for r in run.get("task_results", []) for c in r.get("citations", [])]
        source_names = []
        for cid in citations:
            chunk = store.chunk(cid)
            if chunk:
                source_names.append(chunk["source_name"])
        evidence_present = bool(citations)
        automated_locator_ok = run["metrics"].get("citation_locator_validity") in (1, 1.0, None)
        expected_mode = case["expected_evidence"]
        evidence_behavior_ok = evidence_present if expected_mode == "present" else not evidence_present
        source_match = True if not case.get("expected_source") else case["expected_source"] in source_names
        rows.append({
            "case_id": case["id"],
            "query": case["query"],
            "expected_evidence": expected_mode,
            "expected_source": case.get("expected_source") or "",
            "status": run["status"],
            "citations": ";".join(citations),
            "citation_sources": ";".join(source_names),
            "locator_valid": automated_locator_ok,
            "evidence_behavior_ok": evidence_behavior_ok,
            "source_match": source_match,
            "llm_calls": run["metrics"]["llm_calls"],
            "input_tokens": run["metrics"]["input_tokens"],
            "output_tokens": run["metrics"]["output_tokens"],
            "retrieval_latency_ms": run["metrics"]["retrieval_latency_ms"],
            "e2e_latency_ms": run["metrics"]["latency_ms"],
            "peak_rss_mb": run["metrics"].get("peak_rss_mb"),
            "gpu_memory_mb": run["metrics"].get("gpu_memory_mb"),
            "run_id": run["run_id"],
            "manual_correctness": "UNSCORED",
            "manual_faithfulness": "UNSCORED",
        })
        print(case["id"], run["status"], citations, run["metrics"]["latency_ms"], "ms")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = ROOT / "reports" / "calibration"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"m0_calibration_{args.provider}_{stamp}.json"
    csv_path = out_dir / f"m0_calibration_{args.provider}_{stamp}.csv"
    json_path.write_text(json.dumps({"provider": args.provider, "corpus_snapshot": store.snapshot_id(), "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print({"json": str(json_path), "csv": str(csv_path), "cases": len(rows)})

if __name__ == "__main__":
    asyncio.run(main())
