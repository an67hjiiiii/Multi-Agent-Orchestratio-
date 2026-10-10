from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any, Mapping

from app.run.contracts import Run

class RunStore:
    def __init__(self, root: str = "runs"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, run: Run | Mapping[str, Any]) -> None:
        typed_run = run if isinstance(run, Run) else Run.from_mapping(run)
        payload = typed_run.to_dict()
        run_id = payload["run_id"]
        self._run_path(run_id).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _run_path(self, run_id: str) -> Path:
        if not isinstance(run_id, str) or re.fullmatch(r"[A-Za-z0-9_-]+", run_id) is None:
            raise ValueError("run_id must be a safe filename component")
        path = self.root / f"{run_id}.json"
        if path.resolve().parent != self.root.resolve():
            raise ValueError("run_id must stay inside the run store")
        return path

    def get(self, run_id: str) -> dict | None:
        try:
            path = self._run_path(run_id)
        except ValueError:
            return None
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list(self, limit: int = 30, *, owner_id: str | None = None) -> list[dict]:
        rows: list[dict] = []
        for path in sorted(self.root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                item = json.loads(path.read_text(encoding="utf-8"))
                if owner_id is not None and (
                    not owner_id or item.get("owner_id") != owner_id
                ):
                    continue
                rows.append({k: item.get(k) for k in ("run_id","created_at","condition","query","status")})
                if len(rows) >= limit:
                    break
            except Exception:
                continue
        return rows
