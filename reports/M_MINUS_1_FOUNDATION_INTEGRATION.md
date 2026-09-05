# M-1I Foundation Integration Gate

Date: 2026-09-06 (Asia/Saigon)
Branch: `codex/foundation-integration`
Baseline: `d7fb275` (`m0-code-candidate-pre-gate`)
Integrated HEAD: `5e782f7`

## Decision

`FOUNDATION_PARTIAL`

The seven reviewed Foundation commits integrated cleanly in the required order. Backend, API smoke, policy, compile/import, YAML, and frontend build checks pass. The frontend test gate is not runnable because the committed `frontend/package.json` has no `test` script and does not declare Vitest.

## Cherry-picked commits

1. `33887ea` governance
2. `5f02ac6` frontend-config
3. `83d083b` frontend-shell
4. `3d15e36` backend-api
5. `d198fbc` storage
6. `ae227926` qa-tooling
7. `b27e4c8` ci-docs

Each cherry-pick completed without a conflict or working-tree residue.

## Validation evidence

- Git status was clean before validation; `git diff --check` passed.
- Python compile passed using an isolated temporary bytecode cache.
- Python imports passed for `app.main`, `app.api.router`, and `app.storage.sqlite_store`.
- `.project/project-profile.yaml`, `.project/framework-ref.yaml`, and `.project/project-state.yaml` parsed as dictionaries.
- Full backend suite: `20 passed, 2 warnings`.
- Foundation policy gate: PASS.
- Foundation backend gate (`scripts/check_foundation.py --skip-frontend`): PASS.
- FastAPI smoke with temporary data/run directories and `PROVIDER=fake`: health `200`, text source import `200`, M0/A chat `COMPLETE`, unsupported B rejected `400`.
- Frontend `npm ci`: PASS; production `npm run build`: PASS.
- Frontend `npm test -- --runInBand`: FAIL/UNAVAILABLE because npm reports `Missing script: "test"`; Vitest is absent from `package.json`.
- Provider boundary: only Fake and local Ollama are exposed by `app/providers/factory.py`; no hosted provider match was found in `app` or `frontend`.
- No `app/research` or `app/providers` files changed relative to baseline; no new M1/M2 implementation was introduced by this integration. Existing baseline research code was not treated as proof of M1/M2 completion.
- M0 calibration and live/local Ollama inference were not run, per hard stop.

## Follow-up required

Add an explicit frontend test runner/script (or document an approved alternative) and rerun the frontend contract gate before promoting this result to `FOUNDATION_PASS` or creating `foundation-v1-pre-m0`.

