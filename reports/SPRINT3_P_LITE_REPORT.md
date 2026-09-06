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

The uncommitted PLITE-02 diagnosis delta adds the root `AGENTS.md` project
contract and versions/reorders the decomposer prompt as
`p-lite-decomposer-v2`. It is intentionally left uncommitted pending an
explicit commit authorization.

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
- `P_LITE_RUNTIME`: `PASS` — the controlled direct-schema rerun returned the
  required PLITE-02 two-task chain within the unchanged two-call budget.
- `PILOT`: `PASS` for the Sprint 3 structural gate — the prior four passing
  frozen cases remain recorded and the controlled PLITE-02 prerequisite is now
  satisfied; Task Coverage remains `NOT_SCORED` by design.
- `TASK_COVERAGE`: `NOT_SCORED` by frozen pilot design.
- `M0_REGRESSION`: `PASS`.
- `FINAL_HEAD`: `4cef265`; this controlled delta is intentionally uncommitted.

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

## PLITE02_DIAGNOSIS_DELTA

### Root cause and first failure

The supported diagnosis is a combination of prompt/repair weakness and local
model structured-output reliability, not planning-evidence drift or a
validator defect. Planning Retrieval returned the relevant
`p-lite.database.v1` item. In prompt v1, dynamic request/evidence preceded
the static task/schema rules. Its first raw result merged the two explicit
obligations, omitted `depends_on`, and made `expected_output` an object; the
first failure was the parser's required-string check for `expected_output`.
The v1 repair focused on that formatting error and did not preserve the
separate-chain requirement.

### One prompt delta

`app/research/decomposer.py` now exposes version
`p-lite-decomposer-v2`. Its static common/role prefix comes first: output
protocol, compact JSON schema, and stable planner constraints. The dynamic
suffix then carries the request, planning evidence, and any repair data. The
repair note explicitly retains distinct obligations and required dependencies.
The stable prefix contains no timestamp, run ID, dynamic path, or evidence.
This improves static-prefix/cache-friendly ordering; prompt caching remains a
runtime optimization, not a research claim.

### Captured trace (local `qwen3:4b`)

| Stage | Evidence |
|---|---|
| Planning evidence | `p-lite.database.v1` — database guidance explicitly says schema/data-model and query/access obligations may be separated. |
| V1 call 1 | One `T1`; it semantically merged model and query/access work, omitted `depends_on`, and emitted object-valued `expected_output`. Parser rejected `expected_output`. |
| V1 repair | One `T1`, string `expected_output`, but still omitted `depends_on` and still merged the chain. |
| V2 call 1 | One schema-valid `T1` with `depends_on: []`; coverage validator correctly rejected the merged explicit ordered obligation. |
| V2 repair | Valid `T1` and `T2` with `T2.depends_on=["T1"]`, then an extra malformed third record without `task_id`; parser correctly rejected the response. |
| Final TaskPlan | `FAILED` after the permitted two calls. No invalid task was silently retained or repaired. |

Raw output is retained in the execution trace above as field-level evidence:
v1 call 1 had object `expected_output`; v1 repair remained one task; v2 call 1
had one otherwise valid task; v2 repair contained a valid two-task chain plus
a third malformed record without `task_id`.

Raw excerpts captured before and after the delta:

```text
v1 call 1: T1 only; expected_output={"alignment_status":"confirmed",...};
           depends_on omitted.
v1 repair: T1 only; expected_output="A structured description ...";
           depends_on omitted.
v2 call 1: T1 only; expected_output="Structured description ...";
           depends_on=[].
v2 repair: T1 valid, T2 valid with depends_on=["T1"], followed by a malformed
           third record with no task_id.
```

### Exact result and validation

- `PLITE-02`: `FAILED` after two local calls; expected exactly two tasks and
  one dependency edge, but no parser-valid final task plan was produced.
- `PLITE02_TASK_COVERAGE`: `NOT_SCORED` by frozen structural-pilot design.
- Prompt-v2 focused planner/P-lite tests: PASS — 24 passed.
- Full pytest was not rerun after prompt v2 because PLITE-02 did not pass, per
  the delta validation rule. The prior full suite remains PASS — 110 passed.
- Prompt token comparison from raw captures: v1 952 total tokens (736 input,
  216 output); v2 1,012 total tokens (686 input, 326 output). Direct raw
  capture did not record monotonic latency, so no latency comparison is made.

### Files changed in this delta

- `AGENTS.md` — project contract and cache-friendly prompt policy.
- `app/research/decomposer.py` — prompt v2 ordering and repair preservation.
- `tests/test_decomposer.py` — static-prefix and repair-contract assertions.

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

None for the Sprint 3 P-lite structural gate. M0 remains
`TECHNICAL_PASS` / `HUMAN_REVIEW_PENDING`; this technical result does not
replace its human gate.

## DECISION

`SPRINT3_P_LITE_PASS`

## OWNER_MILESTONE_APPROVAL

- `P_LITE_IMPLEMENTATION_DONE`
- `EMPIRICAL_VALIDATION_PENDING`

The owner approved the current P-lite implementation contract: versioned
Planning KB, relevance-gated bounded retrieval, structured decomposition,
fallback behavior, feature flag, trace, and the recorded focused/full test
results. This does not claim empirical answer-quality improvement; live local
LLM and comparative validation remain pending under a later authorized pilot.

## NEXT

Stop at the Sprint 3 gate. Do not start N, O, Sprint 4, a multi-agent
executor, or a final benchmark from this report. Do not push.

## PLITE02_STRUCTURED_OUTPUT_CONTROLLED_DELTA

### Adapter and config

The existing adapter is a local-only `httpx.AsyncClient` integration with
`POST http://127.0.0.1:11434/api/chat`; it does not use the Ollama Python
library. Its prior `format: "json"` marker was replaced for P-lite planner
generation only by a direct JSON Schema in the same `format` field. This is
supported by Ollama's `/api/chat` structured-output contract.

- Adapter behavior version: `ollama-json-schema-v1`.
- P-lite structured-output configuration version:
  `ollama-task-plan-schema-v1`.
- Planner format: `TaskPlan.model_json_schema()` where `TaskPlan` is the
  existing raw planner object `{ "tasks": [TaskItem, ...] }`; every current
  `TaskItem` field remains required by that schema.
- Planner temperature: `0.0` for this structured-output call only. No other
  sampling parameter changed; model, provider policy, prompt v2 semantic
  instructions, and the two-call ceiling are unchanged.
- The existing JSON parser, required-field checks, dependency validator, and
  ordered-obligation coverage validator remain after generation. No validator
  was bypassed or relaxed.

### Captured PLITE-02 run

Binding: local `ollama` / `qwen3:4b`; prompt version
`p-lite-decomposer-v2`; planning evidence
`p-lite.database.v1`; frozen request unchanged. The full prompt had its
static protocol/schema/rules prefix followed by the current request and
planning evidence. The second call appended only the existing repair suffix:
`Previous validation failure: explicitly ordered obligations require separate
tasks.` Both requests carried the same direct `TaskPlan` JSON Schema and
`temperature: 0.0`.

| Call | Raw output and validation | Tokens | Latency |
| --- | --- | ---: | ---: |
| 1 | Schema-valid JSON with one complete `T1`, `depends_on: []`. The post-generation ordered-obligation validator rejected it because it collapsed the required two-task chain. | 323 input + 93 output | 12,006 ms |
| 2 | Schema-valid JSON with complete `T1` and `T2`; `T2.depends_on=["T1"]`. The parser, dependency validator, and coverage validator accepted it. | 363 input + 176 output | 6,266 ms |

Raw call 1:

```json
{"tasks":[{"task_id":"T1","title":"Review database model","objective":"Identify the structure and constraints of the database model","expected_output":"Structured description of the database schema including tables, columns, relationships, and constraints","domain":"database","role_profile":"Database model reviewer","depends_on":[]}]}
```

Raw call 2 and final `TaskPlan`:

```json
{"tasks":[{"task_id":"T1","title":"Review data model","objective":"Identify the structure and constraints of the database schema","expected_output":"A clear description of the database schema including tables, columns, relationships, and data types","domain":"database","role_profile":"Database analyst","depends_on":[]},{"task_id":"T2","title":"Check query alignment","objective":"Verify that the query matches the database schema structure","expected_output":"Confirmation that the query adheres to the schema constraints and data model","domain":"database","role_profile":"Database validator","depends_on":["T1"]}]}
```

Final task count is exactly `2`; task IDs are `T1`, `T2`; dependency map is
`T1: []`, `T2: ["T1"]`; chain is `T1 -> T2`, with one edge and no cycle.
The run used exactly two LLM calls, 686 input tokens, 269 output tokens,
955 total tokens, and 18,273 ms end-to-end decomposition latency. Ollama
provided token counts; latency is a local monotonic wall-clock measurement.

### Classification and regression

- `SCHEMA_VALIDITY`: PASS for both raw outputs under the direct schema and
  the unchanged post-generation parser.
- `TASK_COUNT_AND_CHAIN`: PASS on call 2 — exactly two tasks and `T1 -> T2`.
- `CLASSIFICATION`: `FORMAT_FIXED_SEMANTIC_PASS`.
- Focused provider/decomposer/P-lite/planning tests: PASS — 31 passed.
- Full backend pytest after PLITE-02 pass: PASS — 112 passed, 2 existing
  deprecation warnings.
- Frontend test/build/typecheck: not rerun because this backend-only delta did
  not touch frontend files; the prior recorded frontend gates remain PASS.
- `TASK_COVERAGE`: `NOT_SCORED`, unchanged by the frozen structural-pilot
  contract (no approved obligation annotations).

### Files changed

This controlled delta changes `app/providers/ollama.py`,
`app/research/task_schema.py`, `app/research/decomposer.py`,
`tests/test_ollama_provider.py`, `tests/test_decomposer.py`, and this report.
The prior uncommitted `AGENTS.md` and prompt-v2 work remain separate; planner
prompt wording was not changed in this delta.

### Final controlled-delta decision

`GO` — `FORMAT_FIXED_SEMANTIC_PASS`. Stop after this Sprint 3 P-lite gate;
do not start N, O, Sprint 4, commit, or push.
