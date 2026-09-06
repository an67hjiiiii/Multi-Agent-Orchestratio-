# Sprint 3 P-lite final integration report

## BASE

- M0/Sprint 3 base contract: `312e676`.
- M0 evidence commits integrated before Sprint 3: `2e6fd27`, `bc5d96d`, and
  `e2c61a9`.
- Sprint 3 worker commits integrated cleanly into `main` (no cherry-pick
  conflict): `fc4e008`, `67852f6`, `23a4b05`, `5c82a20`, `ec9a94a`,
  `09b5500`, `df9bed8`, `406d092`, `10d66ab`, and `3b92ead`.
- Final-blockers delta base: `bc70023`.

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

Final-blockers commit `ee0babf` resolves an explicit provider name through the
existing local-only factory, adapts canonical Pydantic decomposition models at
the legacy runtime boundary, serializes canonical Pydantic task output, and
adds bounded ordered-obligation validation plus a single repair path.

## TESTS

| Check | Result |
|---|---|
| Environment root cause | PASS — all four missing packages were already declared; environments had not been restored |
| Dependencies restored | PASS — local `.venv` from `requirements.txt`; `npm ci` from `frontend/package-lock.json` using an isolated temporary npm cache |
| Manifest changes | NONE |
| Git whitespace check | PASS |
| Git object integrity | PASS |
| P-lite scope scan | PASS — no normalizer, O allocator, scheduler, executor, or synthesis import in the P-lite pipeline |
| Backend `pytest -q` | PASS — 110 passed, 2 warnings |
| Frontend `npm test` | PASS — 6 files, 21 tests |
| Frontend `npm run build` | PASS — `tsc -b` and Vite production build |
| Typecheck | PASS — included in `npm run build` (`tsc -b`) |
| Focused provider/decomposer/P-lite/B-dev/M0 tests | PASS — 23 passed |
| FastAPI P-lite smoke | PASS at HTTP boundary — `m1` `/api/tasks/decompose` returned HTTP 200; Fake structured output is not semantic evidence |
| M0 FastAPI regression | PASS — Fake local smoke: health 200, source import 200, A chat `COMPLETE`, B rejected 400 |

## VERIFICATION_RECORD

- `ENVIRONMENT_ROOT_CAUSE`: declared project dependencies were absent from the active local environments.
- `DEPENDENCIES_RESTORED`: local `.venv` installed from `requirements.txt`; frontend installed with lockfile-based `npm ci`.
- `MANIFEST_CHANGES`: `NONE`.
- `PYTEST`: `PASS` — 110 passed, 2 warnings.
- `FRONTEND_TEST`: `PASS` — 21 tests.
- `FRONTEND_BUILD`: `PASS`.
- `TYPECHECK`: `PASS` through `tsc -b`.
- `FASTAPI_SMOKE`: `PASS` for M0 Fake local smoke.
- `P_LITE_RUNTIME`: `PARTIAL` — local Ollama preserves the one-repair-call budget but PLITE-02 remains terminal `FAILED` after bounded validation.
- `PILOT`: `PARTIAL` — the final PLITE-02 prerequisite recheck failed, so a new complete set was not run.
- `TASK_COVERAGE`: `NOT_SCORED` by frozen pilot design.
- `M0_REGRESSION`: `PASS`.
- `FINAL_HEAD`: `ee0babf` before this report update.

## FINAL_BLOCKERS_DELTA

- `PROVIDER_POLICY_ROOT_CAUSE`: an explicit raw provider name was validated as
  an adapter object before it could use the existing provider factory.
- `PROVIDER_POLICY_FIX`: `PLitePipeline` resolves string provider input through
  `get_provider`; the factory remains the sole local-only allowlist.
- `PROVIDER_POLICY_TESTS`: PASS — explicit `fake` resolves; `openai` remains
  rejected with the local-only policy message.
- `ASDICT_ROOT_CAUSE`: the legacy B/dev runtime treated a Pydantic
  `DecompositionResult` and `TaskItem` as dataclass lists.
- `ASDICT_FIX`: the runtime maps canonical `TaskItem.model_dump()` values to
  its existing `Task` execution contract; P-lite result serialization uses
  `model_dump()` for Pydantic tasks.
- `ASDICT_TESTS`: PASS — B/dev regression and M0 A regression are covered by
  the full pytest run.
- `PLITE02_ROOT_CAUSE`: Planning Retrieval supplied `p-lite.database.v1`, but
  local `qwen3:4b` repeatedly returned malformed or collapsed structured
  output rather than the required two-task dependency chain.
- `PLITE02_FIX`: generic prompt coverage guidance and validation reject a
  collapsed explicitly ordered plan; the default decomposer owns one repair
  retry, preventing wrapper retry multiplication.
- `PLITE02_TASKS`: terminal `FAILED`; no valid tasks after the final bounded
  recheck.
- `PLITE02_DEPENDENCIES`: unavailable because no valid task list survived
  schema and coverage validation.
- `PLITE02_TASK_COVERAGE`: `NOT_SCORED` by the frozen structural pilot design.
- `LOCAL_ONLY_POLICY`: PASS — only FakeProvider and local Ollama are accepted;
  no cloud provider was introduced or invoked.

## PILOT_RESULTS

The pre-delta frozen cases ran serially against the existing local-only Ollama
adapter and `qwen3:4b` (`config_hash: 22a44fda37815fb2`). `PLITE-01`,
`PLITE-03`, `PLITE-04`, and `PLITE-05` emitted `COMPLETE`; `PLITE-02` emitted
one task instead of the required two-task chain. The pilot therefore does not
meet its structural acceptance contract.

After `ee0babf`, the mandatory PLITE-02 recheck remained terminal `FAILED`
within two local calls (14,632 ms, 1,125 total tokens) because the returned
structured response still omitted required schema content. The generic
validator preserved the failure rather than inventing or merging tasks. A new
complete pilot set was correctly not run after this failed prerequisite.

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

`PLITE-02` remains open: real local `qwen3:4b` did not produce a valid
two-task chain inside the bounded two-call structured-output budget. Provider
policy and B/dev serialization blockers are resolved. This is a runtime/model
behavior gate, not an environment blocker; no output was fabricated and no
production code was changed merely to suppress the gate.

## DECISION

`SPRINT3_P_LITE_PARTIAL`

## NEXT

Stop at the Sprint 3 gate. Do not start N, O, Sprint 4, a multi-agent
executor, or a final benchmark from this report.
