from __future__ import annotations
import sys
from pathlib import Path as _Path
_ROOT_FOR_IMPORT = _Path(__file__).resolve().parents[1]
if str(_ROOT_FOR_IMPORT) not in sys.path:
    sys.path.insert(0, str(_ROOT_FOR_IMPORT))
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("IMPLEMENTATION_PROFILE", "m0")
from app.core.config import RuntimeConfig
from app.storage.source_store import SourceStore


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def git_state() -> dict:
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
        return {"commit": commit, "dirty": dirty}
    except Exception:
        return {"commit": None, "dirty": None}

cfg = RuntimeConfig.from_env()
store = SourceStore(os.getenv("APP_DATA_DIR", str(ROOT / "data")))
tracked = [
    ROOT / "requirements.txt",
    ROOT / "config" / "conditions.json",
    ROOT / "datasets" / "calibration" / "m0_cases.json",
]
manifest = {
    "manifest_schema": "m0-release-v1",
    "created_at": datetime.now(timezone.utc).isoformat(),
    "milestone": "M0",
    "claim_status": "CANDIDATE_ONLY_UNTIL_LOCAL_GATE_PASSES",
    "runtime_config": cfg.public_dict(),
    "config_hash": cfg.config_hash(),
    "python": sys.version,
    "platform": platform.platform(),
    "git": git_state(),
    "corpus_snapshot_id": store.snapshot_id(),
    "files": {str(p.relative_to(ROOT)): sha256(p) for p in tracked if p.exists()},
    "notes": [
        "M0 is not DONE until the Ollama/local-model calibration and restore gate are executed on the target laptop.",
        "Fake-provider runs validate wiring only and cannot prove local-LLM completion.",
    ],
}
out = ROOT / "config" / "releases" / "m0_candidate_manifest.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print(out)
