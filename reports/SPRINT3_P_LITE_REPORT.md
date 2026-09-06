# Sprint 3 P-lite final integration report

## BASE

- M0/Sprint 3 base contract: `312e676`.
- M0 evidence commits integrated before Sprint 3: `2e6fd27`, `bc5d96d`, and
  `e2c61a9`.
- Sprint 3 worker commits integrated cleanly into `main` (no cherry-pick
  conflict): `fc4e008`, `67852f6`, `23a4b05`, `5c82a20`, `ec9a94a`,
  `09b5500`, `df9bed8`, `406d092`, `10d66ab`, and `3b92ead`.

## M0_TECHNICAL_STATE

`PASS`

## M0_HUMAN_GATE

`PENDING` — Human correctness and faithfulness scores remain unscored. This
report does not approve M0 or create a release tag.

## WORKERS_CREATED

10 isolated implementation workers and 5 domain verification tasks were
created before the orchestration reuse rule update. No replacement or duplicate
task was created after that update. Future fixes and continuation work reuse the
existing domain thread/worktree where available; Terra performs the one final
integration in this checkout.

## TASK_IDS

Implementation client IDs: `d95706c7`, `8145eb48`, `33b31f63`, `6fd748a1`,
`2b9a9a30`, `07599e0c`, `20a5afe4`, `043406f2`, `14f461b6`, and `99328cf8`.

Domain verification client IDs: `92fbe707`, `57a3f83d`, `57cd6394`,
`aa410876`, and `ea9bad08`.

## SPRINT_MEMBER_MAP

| Member | Delivered scope |
|---|---|
| 1 | P-lite API boundary and pipeline wiring |
| 2 | Task inspection and planning-evidence panels |
| 3 | Separate local Planning KB and planning retrieval |
| 4 | Task schema, dependency validation, and local decomposer |
| 5 | Task Coverage metric and structural pilot contract |

## COMMITS

The worker commits listed in **BASE** contain the P-lite implementation. Final
integration commits `1d57be7`, `21533e2`, and `a48baad` wire `ApiRuntime` to
resolve the selected local provider, serialize the inspection payload at the
HTTP boundary, and expose the Plan inspector only for P-lite profiles. The
locked M0 inspector does not expose that action or tab.

## TESTS

| Check | Result |
|---|---|
| Environment root cause | PASS — all four missing packages were already declared; environments had not been restored |
| Dependencies restored | PASS — local `.venv` from `requirements.txt`; `npm ci` from `frontend/package-lock.json` using an isolated temporary npm cache |
| Manifest changes | NONE |
| Git whitespace check | PASS |
| Git object integrity | PASS |
| P-lite scope scan | PASS — no normalizer, O allocator, scheduler, executor, or synthesis import in the P-lite pipeline |
| Backend `pytest -q` | FAIL — 103 passed, 2 failed, 2 warnings |
| Frontend `npm test` | PASS — 6 files, 21 tests |
| Frontend `npm run build` | PASS — `tsc -b` and Vite production build |
| Typecheck | PASS — included in `npm run build` (`tsc -b`) |
| Focused planning/decomposer/pilot/Ollama contract tests | PASS — 31 passed |
| FastAPI P-lite smoke | PASS at HTTP boundary — `m1` `/api/tasks/decompose` returned HTTP 200; Fake structured output is not semantic evidence |
| M0 FastAPI regression | PASS — Fake local smoke: health 200, source import 200, A chat `COMPLETE`, B rejected 400 |

## VERIFICATION_RECORD

- `ENVIRONMENT_ROOT_CAUSE`: declared project dependencies were absent from the active local environments.
- `DEPENDENCIES_RESTORED`: local `.venv` installed from `requirements.txt`; frontend installed with lockfile-based `npm ci`.
- `MANIFEST_CHANGES`: `NONE`.
- `PYTEST`: `FAIL` — 103 passed, 2 failed, 2 warnings.
- `FRONTEND_TEST`: `PASS` — 21 tests.
- `FRONTEND_BUILD`: `PASS`.
- `TYPECHECK`: `PASS` through `tsc -b`.
- `FASTAPI_SMOKE`: `PASS` for M0 Fake local smoke.
- `P_LITE_RUNTIME`: `PARTIAL` — local Ollama runtime completes requests but the frozen pilot contains one structural mismatch.
- `PILOT`: `PARTIAL` — PLITE-02 did not match its required task-graph shape.
- `TASK_COVERAGE`: `NOT_SCORED` by frozen pilot design.
- `M0_REGRESSION`: `PASS`.
- `HEAD`: `883ee33` at verification start.

## PILOT_RESULTS

`PARTIAL`. The frozen cases ran serially against the existing local-only Ollama
adapter and `qwen3:4b` (`config_hash: 22a44fda37815fb2`). `PLITE-01`,
`PLITE-03`, `PLITE-04`, and `PLITE-05` emitted `COMPLETE`; `PLITE-02` emitted
one task instead of the required two-task chain. The pilot therefore does not
meet its structural acceptance contract.

Observed P-lite runtime metrics: PLITE-01 14,846 ms/1 call; PLITE-02 4,262
ms/1 call; PLITE-03 10,268 ms/1 call; PLITE-04 8,724 ms/2 calls; PLITE-05
3,903 ms/1 call. PLITE-04 recorded an empty planning context warning, which
is an allowed observation for its ambiguous case.

## TASK_COVERAGE

`NOT_SCORED`, as required by the frozen structural-only pilot: no approved
obligation annotations were supplied. The Task Coverage implementation and
focused tests are present; no score was inferred from task count or titles.

## LATENCY

Recorded for the serial local P-lite pilot above. These are bounded structural
pilot measurements, not a calibration or cross-hardware comparison.

## BLOCKERS

1. `tests/test_p_lite_pipeline.py::test_p_lite_rejects_non_local_provider_names`
   expects the local-provider policy wording but a raw provider name reaches
   the generic adapter-object error path.
2. `tests/test_pipeline.py::test_a_b_c_fake_dev_profile` fails in the existing
   B/dev path because `asdict()` receives a non-dataclass task object.
3. Live `PLITE-02` did not meet its frozen two-task-chain shape contract.

These are backend/P-lite follow-ups, not environment or dependency blockers.
No production code was changed to suppress them.

## DECISION

`SPRINT3_P_LITE_PARTIAL`

## NEXT

Stop at the Sprint 3 gate. Reuse the existing Backend, Planning Retrieval,
Decomposer, and QA domain work before rerunning the failed backend regression
and frozen pilot. Do not start N, O, Sprint 4, a multi-agent executor, or a
final benchmark from this report.
