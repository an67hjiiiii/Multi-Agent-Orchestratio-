# Pre-pilot closure baseline

Captured before the scoped O trace-label correction and without touching historical raw evidence.

| Check | Result | Evidence |
| --- | --- | --- |
| HEAD before | `d781d8e` | `git rev-parse HEAD` |
| Backend regression | PASS — 132 passed, 2 warnings | initial closure baseline |
| Frontend unit tests | PASS — 21 passed | `frontend/npm.cmd test` |
| Frontend production build | PASS | `frontend/npm.cmd run build` |
| FastAPI TestClient smoke | PASS | A/Fake wiring smoke only; not semantic evidence |
| Ollama tags | PASS — local `qwen3:4b` present | `GET /api/tags` |
| Ollama version | `0.33.3` | `GET /api/version` |
| Git whitespace | PASS | `git diff --check` |

Existing untracked evidence was preserved in place: `reports/m1_pilot/`,
`runs/m1_pilot/`, `reports/pre_m2_audit_bundle/`, and
`reports/pre_m2_audit_bundle.zip`. No historical attempt was modified,
canonicalized, retried, or deleted.
