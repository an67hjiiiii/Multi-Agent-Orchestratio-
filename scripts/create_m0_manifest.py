from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import RuntimeConfig
from app.storage.source_store import SourceStore


MANIFEST_SCHEMA = "m0-release-v1"
CLAIM_STATUS = "CANDIDATE_ONLY_UNTIL_LOCAL_GATE_PASSES"

# Keep the manifest bound to the code and inputs that can change M0 output.
# The release file itself is intentionally excluded to avoid a hash cycle.
DEFAULT_TRACKED_FILES = (
    "requirements.txt",
    ".project/project-profile.yaml",
    ".project/framework-ref.yaml",
    "config/conditions.json",
    "datasets/calibration/m0_cases.json",
    "app/core/config.py",
    "app/core/telemetry.py",
    "app/core/types.py",
    "app/providers/factory.py",
    "app/providers/fake.py",
    "app/providers/ollama.py",
    "app/research/pipeline.py",
    "app/research/vanilla.py",
    "app/retrieval/text.py",
    "app/storage/source_store.py",
    "scripts/run_m0_calibration.py",
    "scripts/create_m0_manifest.py",
    "docs/M0_STATUS.md",
    "docs/M0_TRACE_METRICS.md",
)

TRACE_METRICS_CONTRACT = {
    "document": "docs/M0_TRACE_METRICS.md",
    "identity": [
        "run_id",
        "condition",
        "implementation_profile",
        "provider",
        "model",
        "source_snapshot_id",
        "config_hash",
        "status",
    ],
    "metrics": [
        "llm_calls",
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "retrieval_latency_ms",
        "generation_latency_ms",
        "latency_ms",
        "peak_rss_mb",
        "gpu_memory_mb",
        "citation_locator_validity",
    ],
}


def sha256(path: Path) -> str:
    """Return the SHA-256 digest of a file without loading it all at once."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_state(root: Path = ROOT) -> dict[str, str | bool | None]:
    """Return checkout identity without exposing command errors in the manifest."""
    try:
        commit_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
        status_result = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
        return {
            "commit": commit_result.stdout.strip() or None,
            "dirty": bool(status_result.stdout.strip()),
        }
    except Exception:
        return {"commit": None, "dirty": None}


def _utc_iso(value: datetime | None) -> str:
    if value is None:
        value = datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _data_directory(root: Path) -> Path:
    configured = os.getenv("APP_DATA_DIR")
    if not configured:
        return root / "data"
    path = Path(configured)
    return path if path.is_absolute() else root / path


def build_manifest(
    root: Path = ROOT,
    *,
    data_dir: Path | None = None,
    created_at: datetime | None = None,
) -> dict:
    """Build an M0 candidate manifest without writing the release file."""
    root = Path(root).resolve()
    cfg = RuntimeConfig.from_env()
    if cfg.implementation_profile != "m0":
        raise ValueError(
            "M0 manifest generation requires IMPLEMENTATION_PROFILE=m0; "
            f"received {cfg.implementation_profile!r}"
        )

    corpus_dir = Path(data_dir) if data_dir is not None else _data_directory(root)
    if not corpus_dir.is_absolute():
        corpus_dir = root / corpus_dir
    store = SourceStore(str(corpus_dir))

    file_hashes = {}
    missing_files = []
    for relative_path in DEFAULT_TRACKED_FILES:
        path = root / relative_path
        if path.is_file():
            file_hashes[relative_path] = sha256(path)
        else:
            missing_files.append(relative_path)

    return {
        "manifest_schema": MANIFEST_SCHEMA,
        "created_at": _utc_iso(created_at),
        "milestone": "M0",
        "claim_status": CLAIM_STATUS,
        "allowed_conditions": cfg.allowed_conditions(),
        "runtime_config": cfg.public_dict(),
        "config_hash": cfg.config_hash(),
        "model": {
            "tag": cfg.local_model,
            "status": "calibration-candidate",
            "research_frozen": False,
        },
        "python": sys.version,
        "platform": platform.platform(),
        "git": git_state(root),
        "corpus_snapshot_id": store.snapshot_id(),
        "corpus": {
            "store_file_present": (corpus_dir / "sources.json").is_file(),
            "chunk_count": len(store.chunks()),
        },
        "files": file_hashes,
        "missing_files": missing_files,
        "trace_metrics_contract": TRACE_METRICS_CONTRACT,
        "notes": [
            "M0 is not DONE until the Ollama/local-model calibration and restore gate are executed on the target laptop.",
            "Fake-provider runs validate wiring only and cannot prove local-LLM completion.",
            "Memory metrics are best-effort observations; null means the host did not provide that measurement.",
        ],
    }


def write_manifest(
    manifest: dict,
    output_path: Path = ROOT / "config" / "releases" / "m0_candidate_manifest.json",
) -> Path:
    """Write a previously built manifest and return its path."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


def main() -> int:
    output_path = write_manifest(build_manifest())
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
