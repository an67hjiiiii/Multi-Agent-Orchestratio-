from __future__ import annotations
import json
from pathlib import Path

class RunStore:
    def __init__(self, root: str = "runs"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, run: dict) -> None:
        run_id = run["run_id"]
        (self.root / f"{run_id}.json").write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")

    def get(self, run_id: str) -> dict | None:
        path = self.root / f"{run_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list(self, limit: int = 30) -> list[dict]:
        rows: list[dict] = []
        for path in sorted(self.root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
            try:
                item = json.loads(path.read_text(encoding="utf-8"))
                rows.append({k: item.get(k) for k in ("run_id","created_at","condition","query","status")})
            except Exception:
                continue
        return rows
