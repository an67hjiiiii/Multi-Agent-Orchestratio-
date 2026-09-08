"""Launch or dry-run the reusable final six-condition experiment harness.

The default command is intentionally blocked until both dataset and semantic
gold approval are explicitly supplied as ``APPROVED``.  ``--dry-run`` is safe
while approval is pending and never constructs a provider or pipeline.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.evaluation.final_experiment import (
    FINAL_CONDITIONS,
    PENDING_HUMAN_APPROVAL,
    run_final_experiment,
)

DEFAULT_CASES = ROOT / "datasets" / "final" / "final_benchmark_v1.json"
DEFAULT_OUTPUT = ROOT / "reports" / "final_experiment"
DEFAULT_RUNS = ROOT / "runs" / "final_experiment"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the serial final A/B/C/C-P/C-N/C-O harness.")
    parser.add_argument("--cases-path", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS)
    parser.add_argument("--provider", choices=["fake", "ollama"], default="fake")
    parser.add_argument("--experiment-id", default="final-six-condition-v1")
    parser.add_argument("--experiment-freeze-id", default=PENDING_HUMAN_APPROVAL)
    parser.add_argument("--dataset-status", default=PENDING_HUMAN_APPROVAL)
    parser.add_argument("--gold-status", default=PENDING_HUMAN_APPROVAL)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--conditions", nargs="+", choices=FINAL_CONDITIONS, default=FINAL_CONDITIONS)
    parser.add_argument("--dry-run", action="store_true", help="Print the blocked/ready plan without inference.")
    return parser


async def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = await run_final_experiment(
            cases_path=args.cases_path,
            output_dir=args.output_dir,
            runs_dir=args.runs_dir,
            provider=args.provider,
            experiment_id=args.experiment_id,
            experiment_freeze_id=args.experiment_freeze_id,
            dataset_status=args.dataset_status,
            gold_status=args.gold_status,
            repeats=args.repeats,
            conditions=tuple(args.conditions),
            dry_run=args.dry_run,
        )
    except Exception as exc:
        print(json.dumps({"launch_status": "BLOCKED", "error_type": type(exc).__name__, "message": str(exc)}))
        return 2
    print(json.dumps(result["plan"], ensure_ascii=False, sort_keys=True))
    if result.get("path"):
        print(result["path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
