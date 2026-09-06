# M1 Pilot Report

BASE: `2ff0254`; state authorization commit: `8b046a5`.

STATE_AUTHORIZATION_COMMIT: `8b046a5 chore(state): authorize M1 pilot`.

OLLAMA_RECOVERY: Recovered using the existing binary at
`C:\Users\Viet Anh\AppData\Local\Programs\Ollama\ollama.exe`; no download,
reinstall, or model pull was performed. `ollama serve` was started only because
no Ollama process was running. `GET /api/tags` and the allowlisted adapter
health check both returned READY at the loopback-only endpoint
`http://127.0.0.1:11434`.

OLLAMA_VERSION: `0.33.3` (`GET /api/version`).

MODEL: `qwen3:4b`, present before execution, digest
`359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7`.

PREFLIGHT: PASS. The frozen development/validation manifest has 15 selected
requests, profile `m1` accepted A/B/C, and the shared resolved config hash is
`10e98fbfb8c8d960`. The model executions were serial.

PHASE1_RUNS: 9/9 canonical attempts, using `M1-01` through `M1-03`, A/B/C,
one repeat. No existing historical raw attempt was touched. Artifacts are the
append-only ledger and atomic JSON report under
`reports/m1_pilot/m1-pilot-authorized-v1/`; raw traces are under
`runs/m1_pilot/m1-pilot-authorized-v1/`.

A_RESULTS: 3 `COMPLETE` / 0 `PARTIAL` / 0 `NO_EVIDENCE` / 0 `FAILED`.

B_RESULTS: 0 `COMPLETE` / 2 `PARTIAL` / 1 `NO_EVIDENCE` / 0 `FAILED`.

C_RESULTS: 1 `COMPLETE` / 1 `PARTIAL` / 1 `NO_EVIDENCE` / 0 `FAILED`.

CONDITION_SEMANTICS:

- A traces contain `vanilla_retrieval` only: no decomposition, planning,
  normalization, or overlap stage.
- B traces contain `decomposition` and `task_retrieval`; all B effective flags
  are `P=false`, `N=false`, `O=false`, and no planning/normalization/overlap
  stage occurs.
- C traces show `planning_retrieval` before `decomposition`, then
  `normalization`, task retrieval with `o_enabled=true`, and
  `overlap_summary`. All C effective flags are `P=true`, `N=true`, `O=true`.

The trace contract is therefore exercised rather than inferred from condition
labels. Per-run raw records retain task/dependency data, selected retrieval and
planning evidence, selected/dropped context, citation validity, token/call
counts, latency, RAM, and VRAM where the host provided them. Phase-1 C samples
used 2--3 LLM calls, 411--970 tokens, 8,476--11,377 ms, about 47.82--49.36 MiB
RSS, and 2,332--2,334 MiB VRAM. No Human correctness or faithfulness score was
assigned.

CHECKPOINT_STATE: 9 canonical attempt keys are durable. A resumed runner skips
those exact `case|condition|repeat` keys; it does not regenerate them.

FULL_PILOT: NOT_STARTED. The planned 135 canonical attempts were not started;
the 9 Phase-1 records would have been reused rather than duplicated.

BLOCKERS: Phase 1 is structurally runnable but does not pass its end-to-end
quality gate: all B attempts and two of three C attempts terminate
`PARTIAL`/`NO_EVIDENCE`; B/C partial records also expose citation validity
`0.0` where citations were emitted. This is recorded evidence, not a reason to
retry or alter P/N/O/model/prompt/cases. Full pilot is withheld pending owner
direction on the observed B/C quality/citation failure.

HEAD: `8b046a5` (state authorization checkpoint).

DECISION: M1_PILOT_PARTIAL

## Stability audit and runtime-only citation-gate resume

STABILITY_AUDIT: `ONLY_RUNTIME_BLOCKER`.

AUDIT_BASIS: The last full regression result remains `131 passed, 2 warnings`;
the code commits inspected were `6dea3f6`, `2cffee9`, and `65f49c1`. The
former decomposition/schema and final-synthesis locator defects are covered by
the latter two commits. No code changed during this audit.

RUNTIME_RECOVERY: Local `127.0.0.1:11434/api/tags` responded and confirmed
`qwen3:4b` digest
`359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7`.

LIVE_RECHECK_V3_RUNTIME_RESUME: Immutable namespace
`m1-final-citation-v3-runtime-resume`, C/M1-01, `COMPLETE`; 3 LLM calls,
42,862 ms, citation validity `1.0`. Its rendered locator
`[src_ecad6843b8fcb99b_c0000]` resolves to selected task evidence; no raw
locator leaked. Trace confirms Planning Retrieval before decomposition plus
normalization and overlap-summary events.

CITATION_GATE: PASS for the three actual model generations across immutable v3
namespaces: C/M1-02, B/M1-01, and C/M1-01. The earlier retained `FAILED`
record is a `ConnectError` before generation (`llm_calls=0`), not a remaining
P/N/O, decomposer, citation, or provider-adapter code defect.

FRESH_PHASE1: NOT RUN in this stability-audit delta. It requires the separate
explicit pilot-execution step; no full M1 pilot or M2 work was started.

DECISION: M1_PILOT_PARTIAL

## M1 P/N/O decomposer stabilization and final citation recheck v3

BASE: `6dea3f6` (M1 hardening baseline). The current checked-out integration
head is `65f49c1`.

CITATION_FIX_COMMIT: `2cffee9 fix(m1): canonicalize final synthesis citations`.
The resolver accepts only application-owned evidence keys and final rendering
uses canonical source-chunk IDs that are present in the selected task evidence.

PNO_DECOMPOSER_ROOT_CAUSE: **D1** — the FakeProvider emitted the former
`id`/`goal` fixture shape, while the approved decomposer contract requires the
canonical `TaskItem` fields (`task_id`, `title`, `objective`,
`expected_output`, `domain`, `role_profile`, and `depends_on`). The first
divergence was parser/schema validation: the bounded repair path returned an
empty `FAILED` decomposition. A defensive pipeline boundary also made the
otherwise silent empty-list propagation explicit; this is a failure-state
guard, not a change to P, N, or O semantics.

PNO_DECOMPOSER_FIX: `65f49c1 fix(m1): stabilize fake decomposer contract`
updates FakeProvider's dev fixture to the public TaskItem shape and makes a
failed/empty decomposition terminally `FAILED` rather than an empty
`PARTIAL` result. P/N/O routing, flags, retrieval limits, prompts, and
condition semantics were unchanged.

FOCUSED_TESTS: `25 passed` — pipeline/decomposer/normalizer/O-lite and worker
citation focused coverage, including an explicit invalid-decomposition test.

FULL_PYTEST: `131 passed, 2 warnings` (before any live provider call).

LIVE_RECHECK_V3:

- Immutable namespace `m1-final-citation-v3`: C/M1-02 recorded `FAILED`
  before model generation because the local Ollama endpoint was unreachable.
  Trace: `planner generation failed with ConnectError`; `llm_calls=0`.
  The record is retained and was not rerun or overwritten.
- Existing local Ollama was then restored at `127.0.0.1:11434`; its tag API
  confirmed local `qwen3:4b` digest
  `359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7`.
- Immutable namespace `m1-final-citation-v3-recovered`: C/M1-02 completed
  serially (`3` LLM calls, `40,287 ms`, citation validity `1.0`) and B/M1-01
  completed serially (`3` LLM calls, `32,783 ms`, citation validity `1.0`).
  C trace proves Planning Retrieval before decomposition and N/O invocation;
  B trace proves P/N/O are all off.

FINAL_RENDERED_CITATION_CHECK: PASS for both completed v3 records. Each final
answer renders only `[src_ecad6843b8fcb99b_c0000]`; it belongs to the selected
task evidence, no malformed raw locator was rendered, and each
`citation_locator_validity` metric is `1.0`. The endpoint-outage record has no
model output and no rendered citation to validate.

FRESH_PHASE1: NOT RUN. The maximum three v3 attempt records include one
infrastructure `FAILED` record, so the required clean three-attempt citation
gate was not met. No retry was added and no prior Phase 1 record was changed.

PHASE1_TECHNICAL_GATE: BLOCKED (citation boundary is clean in the two completed
generations, but v3 as a whole is not a clean gate because of the retained
Ollama-connectivity failure).

FULL_M1_PILOT_READY: NO.

HEAD: `65f49c1`.

COMMITS: `2cffee9 fix(m1): canonicalize final synthesis citations`;
`65f49c1 fix(m1): stabilize fake decomposer contract`.

BLOCKERS: Restore and keep the local Ollama service reachable, then obtain
owner authorization for a new bounded immutable citation recheck. Do not
reuse or overwrite either v3 namespace. No P/N/O implementation blocker is
known from the full regression.

DECISION: M1_PILOT_PARTIAL

## Final citation gate delta

HARDENING_COMMIT: `6dea3f6 fix(m1): harden task retrieval and worker citations`.
Only the verified M1 hardening set was committed: worker evidence keys and
deterministic mapping, bounded retrieval fallback, immutable ledger/runner,
frozen manifest, focused tests, and the existing M1 report. Historical raw
attempts were not staged or modified.

SYNTHESIS_CITATION_ROOT_CAUSE: The former synthesis pass treated any canonical
ID occurring anywhere in model text—including `available_evidence`—as proof
that a final citation had been rendered. A malformed model locator could
therefore remain in the final answer while the worker metric was valid.

SYNTHESIS_CITATION_FIX: The final boundary now requires JSON synthesis output
with `E1`-style evidence keys. Application code resolves keys only against the
task-result evidence IDs, rejects unknown/malformed values, and constructs the
final `Nguồn` list exclusively from canonical worker and validated synthesis
IDs. A non-JSON synthesis response falls back to structured task answers,
not untrusted raw locator text. This shares the existing M0 deterministic
citation contract; it adds no second citation system.

FOCUSED_TESTS: PASS — `20 passed` for synthesis evidence-key resolution,
canonical final serialization, malformed/unselected citation rejection,
worker-citation preservation, NO_EVIDENCE citation-freedom, and multiple-task
attribution.

FULL_PYTEST: BLOCKED — `129 passed, 1 failed, 2 warnings`. The sole failure is
`tests/test_pipeline.py::test_a_b_c_fake_dev_profile`: the currently
uncommitted P/N/O/decomposer worktree path emits an empty decomposed task list
for FakeProvider, so the pipeline answer is empty. The same failure was
observed before this synthesis change. It is outside the final-synthesis-only
scope and was not modified.

LIVE_RECHECK_V3: NOT RUN. The required full regression gate is not clean, so
the authorized maximum three qwen3:4b attempts were deliberately not spent.

FINAL_RENDERED_CITATION_CHECK: Unit contract PASS; live verification is
pending the clean full regression gate.

JUSTIFIED_PARTIAL_REASON: The earlier M1-03/B partial remains evidence that
the corpus lacks the requested specific query/identifier detail; it had a
valid canonical worker citation after hardening. No new live assessment was
made in this delta.

PHASE1_FRESH: NOT RUN.

PHASE1_TECHNICAL_GATE: BLOCKED.

FULL_PILOT: NOT STARTED.

COMMITS: `6dea3f6`.

BLOCKERS: `WORKTREE_CONFLICT` — the existing uncommitted P/N/O/decomposer
changes fail the shared Fake pipeline regression. Owner direction or an
authorized integration of that separate track is required before the final
citation delta can enter live recheck. No retrieval/P/N/O code was changed in
this delta, and no M2/ablation/push was performed.

HEAD: `6dea3f6`.

DECISION: M1_PILOT_PARTIAL

The empirical-validation state remains pending. This report does not claim M1
done, research-MVP pass, or comparative A/B/C effectiveness.

## Hardening delta

FAILURE_MATRIX:

| Case | Condition | Final status | First divergence from A | Primary class | Evidence |
|---|---|---|---|---|---|
| M1-01 | B | PARTIAL | worker citation parsing | R5 | selected the same authentication chunk as A, but emitted `src_ecad6843b8fcb99b_c0:0000`; the strict worker validator rejected it. |
| M1-01 | C | PARTIAL | worker citation parsing | R5 | planning, N and O ran; O retained the same authentication chunk, but the worker emitted a mistyped raw locator. |
| M1-02 | B | PARTIAL | worker citation parsing | R5 | selected the same authorization chunk as A, but emitted truncated `src_ecad6:0000`. |
| M1-02 | C | COMPLETE | synthesis output | R6 | worker task citation was canonical, but synthesis rendered `src_ecad6843b8fcb99b_c0:0000` rather than preserving the validated locator. |
| M1-03 | B | NO_EVIDENCE | task-specific retrieval | R2 | A selected `src_1055b8f580d99531_c0000`; decomposed wording lost the lexical `indexes` anchor and returned no candidate. |
| M1-03 | C | NO_EVIDENCE | task-specific retrieval | R2 | same empty candidate set occurred before O selection, so this is not an O filter removal. |

For all six original B/C records, decomposition produced one independent `T1`
task with no dependency, and no Task Coverage metric was recorded by the
current runner. The selected/dropped IDs, worker result, synthesis text, raw
and parsed citation values are retained in their immutable raw JSON traces.
The M1-01/M1-02 partial runs selected one ID and dropped none; their raw worker
citation values were malformed and parsed as invalid. The M1-03 `NO_EVIDENCE`
runs selected no ID, dropped none, and have citation-free worker/synthesis
outputs. This establishes first divergence before code changes.

ROOT_CAUSE_BY_RUN: Original M1-01 B/C and M1-02 B are R5 worker raw-locator
format failures; original M1-02 C additionally exposes R6 synthesis citation
corruption; original M1-03 B/C are R2 task-query retrieval misses. R3 is
ruled out for M1-03 because B (O off) misses identically and C has no candidate
before O. R8/R9 are not established for original M1-03 because A retrieved
the relevant database evidence.

CITATION_ROOT_CAUSE: B/C worker used raw canonical chunk locators while the
M0 path uses application-owned evidence keys. The hardening delta changes the
worker to emit `E1`/`E2` keys and resolves them through the existing
deterministic M0 mapping. A remaining synthesis defect was observed after the
six-attempt recheck: its presence check accepts a canonical ID in an
`available_evidence` field as if it were an emitted citation. It must be fixed
and validated in a separately authorized recheck; it was not changed after the
live-attempt budget was exhausted.

NO_EVIDENCE_ROOT_CAUSE: Decomposition paraphrase can remove the lexical query
anchor used by local retrieval. The hardening delta falls back to the original
user request only if task-specific retrieval returns no candidates. This is
bounded by the existing top-k and token limits and does not add P/N/O behavior
to B.

PARTIAL_ROOT_CAUSE: The recheck fixed citation validity for all six attempts.
M1-03/B remains `PARTIAL` with a valid selected citation because the model
correctly states that the corpus does not identify specific unindexed queries
or identifiers. Its missing-information list records those unavailable facts;
this is not a citation or retrieval failure.

FILES_CHANGED: `app/research/worker.py`, `app/research/pipeline.py`,
`scripts/run_m1_pilot.py`, `tests/test_worker_citations.py`,
`tests/test_pipeline.py`, and this report. No P/N/O contract, model, prompt
budget, top-k, dataset, or frozen pilot case changed.

FOCUSED_TESTS: `19 passed` for worker citation mapping, selected-key rejection,
NO_EVIDENCE citation-freedom, multi-task synthesis preservation, task-query
fallback, retrieval citations, pipeline, and O-lite coverage.

FULL_PYTEST: `128 passed, 2 warnings`.

LIVE_RECHECK: Namespace `m1-pilot-hardening-v2`, six serial B/C attempts:
five `COMPLETE`, one `PARTIAL`, zero `FAILED`, all evidence-bearing worker
outputs have citation validity `1.0`. M1-03/C used the bounded fallback and
completed; M1-03/B selected evidence directly and remained a justified
partial. The six-attempt maximum is exhausted; no retry was performed.

PHASE1_FINAL: NOT PASSED. Although B/C worker retrieval and citation mapping
improved, the unvalidated/corrupted synthesis citation observed in the recheck
prevents a technically acceptable end-to-end citation contract.

FULL_PILOT: NOT STARTED.

BLOCKERS: Fix and focused-test the R6 synthesizer citation-preservation guard,
then obtain authorization for a new bounded live recheck. Do not rerun the
existing 9 Phase-1 records or the six hardening recheck records.

HEAD: `8b046a5`.

DECISION: M1_PILOT_PARTIAL

## Current canonical delta — P/N/O decomposer stabilization and citation recheck v3

BASE: `6dea3f6`; current HEAD: `65f49c1`.

CITATION_FIX_COMMIT: `2cffee9 fix(m1): canonicalize final synthesis citations`.
It permits only application-owned evidence keys and renders canonical selected
source-chunk IDs.

PNO_DECOMPOSER_ROOT_CAUSE: **D1**. FakeProvider emitted the legacy
`id`/`goal` fixture shape rather than the current public TaskItem contract.
The first divergence was decomposer parser/schema validation, whose bounded
failure path returned no tasks. The pipeline had also allowed this empty
failure result to appear as an empty `PARTIAL`.

PNO_DECOMPOSER_FIX: `65f49c1 fix(m1): stabilize fake decomposer contract`
emits canonical TaskItem fields from FakeProvider and turns a failed/empty
decomposition into explicit terminal `FAILED`. It changes neither P/N/O
semantics nor condition routing, prompts, model, limits, or pilot cases.

FOCUSED_TESTS: `25 passed`.

FULL_PYTEST: `131 passed, 2 warnings` before live inference.

LIVE_RECHECK_V3:

- `m1-final-citation-v3`, C/M1-02: retained `FAILED` record before generation
  (`ConnectError`, `llm_calls=0`) while local Ollama was unreachable.
- Ollama was restored locally at `127.0.0.1:11434`; `qwen3:4b` digest was
  `359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7`.
- `m1-final-citation-v3-recovered`, C/M1-02: `COMPLETE`, 3 calls, 40,287 ms,
  citation validity `1.0`; trace shows Planning Retrieval before decomposition
  and N/O invocation.
- `m1-final-citation-v3-recovered`, B/M1-01: `COMPLETE`, 3 calls, 32,783 ms,
  citation validity `1.0`; trace shows P/N/O all disabled.

FINAL_RENDERED_CITATION_CHECK: PASS for both completed records. Every rendered
locator is `[src_ecad6843b8fcb99b_c0000]`, is in selected task evidence, and
has no malformed raw-locator leak. The outage record produced no model output.

FRESH_PHASE1: NOT RUN. One of the maximum three v3 attempt records is the
retained infrastructure `FAILED` record, so the clean three-attempt gate did
not pass; no retry or artifact overwrite was performed.

PHASE1_TECHNICAL_GATE: BLOCKED.

FULL_M1_PILOT_READY: NO.

COMMITS: `2cffee9 fix(m1): canonicalize final synthesis citations`;
`65f49c1 fix(m1): stabilize fake decomposer contract`.

BLOCKERS: A stable local Ollama service plus owner authorization for a new
immutable bounded citation recheck. No P/N/O implementation blocker is known
from full regression.

DECISION: M1_PILOT_PARTIAL

## Current canonical delta — stability audit and runtime-only citation-gate resume

STABILITY_AUDIT: `ONLY_RUNTIME_BLOCKER`.

AUDIT_BASIS: Last full regression: `131 passed, 2 warnings`; inspected commits:
`6dea3f6`, `2cffee9`, and `65f49c1`. The schema/decomposer and final-synthesis
locator defects are fixed in the latter two commits. No code changed during
this audit.

RUNTIME_RECOVERY: `127.0.0.1:11434/api/tags` responded and confirmed local
`qwen3:4b` digest
`359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7`.

LIVE_RECHECK_V3_RUNTIME_RESUME: Immutable namespace
`m1-final-citation-v3-runtime-resume`, C/M1-01: `COMPLETE`; 3 LLM calls,
42,862 ms, citation validity `1.0`. Rendered
`[src_ecad6843b8fcb99b_c0000]` resolves to selected task evidence, with no raw
locator leak. The trace has Planning Retrieval before decomposition, followed
by normalization and overlap-summary.

CITATION_GATE: PASS for the three actual model generations across immutable v3
namespaces: C/M1-02, B/M1-01, and C/M1-01. The retained `FAILED` v3 record is
an Ollama `ConnectError` before generation (`llm_calls=0`), not a P/N/O,
decomposer, citation, or adapter code defect.

FRESH_PHASE1: NOT RUN in this stability-audit delta. It needs the separately
authorized pilot-execution step; no full M1 pilot or M2 work was started.

DECISION: M1_PILOT_PARTIAL

## Current canonical delta — fresh Phase 1

FRESH_PHASE1_NAMESPACE: `m1-phase1-fresh-v1` (immutable, local Ollama,
qwen3:4b, `smoke` phase).

RUNS: 9/9 unique canonical case-condition records; the single-writer lock was
released at completion and the deterministic ledger-derived JSON report exists.

A_RESULTS: 3 `COMPLETE`, 0 `PARTIAL`, 0 `FAILED`, 0 `NO_EVIDENCE`; 3 LLM
calls, 949 total tokens, 6,286 ms total latency.

B_RESULTS: 2 `COMPLETE`, 1 `PARTIAL` (M1-03), 0 `FAILED`, 0 `NO_EVIDENCE`;
9 LLM calls, 4,604 total tokens, 110,598 ms total latency.

C_RESULTS: 2 `COMPLETE`, 1 `PARTIAL` (M1-03), 0 `FAILED`, 0 `NO_EVIDENCE`;
9 LLM calls, 4,833 total tokens, 108,428 ms total latency.

CONDITION_TRACE_CHECK: PASS for condition mechanics. A has only
`vanilla_retrieval` and no decomposition/P/N/O. B has decomposition plus
task-specific retrieval with P/N/O disabled. Every C trace has Planning
Retrieval before decomposition, normalization, task retrieval, and
overlap-summary; C selected the needed evidence and retained it.

CITATION_VALIDITY: PASS. All 9 evidence-bearing records report `1.0`;
9/9 emitted citations are valid.

FINAL_LOCATOR_CHECK: PASS. Each final rendered locator resolves to the
record's selected task evidence; no raw locator leak was observed.

JUSTIFIED_PARTIALS: B/M1-03 is justified by the explicit bounded fallback
trace and its recorded missing-information fields. C/M1-03 is `PARTIAL` with
selected evidence and a valid citation, but has no corresponding
missing-information/reason field. It is therefore not an explicitly justified
partial under this Phase 1 gate.

NO_EVIDENCE_ANALYSIS: PASS — no `NO_EVIDENCE` record occurred.

TRACE_LEDGER_CHECK: PASS — 9 unique canonical records, 9 ledger rows, report
present, lock released, immutable effective configs/config hash/source
snapshot recorded.

M0_REGRESSION: PASS — all three A records completed through the Vanilla RAG
path with no decomposition or P/N/O stages.

PHASE1_TECHNICAL_GATE: PARTIAL. No pipeline-defect `FAILED` record occurred,
but C/M1-03 does not meet the gate's explicit-trace requirement for a
`PARTIAL` result. This is recorded as live evidence, not retried or repaired.

FULL_M1_PILOT_READY: NO.

BLOCKERS: Classify C/M1-03's model-emitted `PARTIAL` without an explicit
missing-information/reason trace, then obtain owner direction before any
additional live run or code change. No human correctness/faithfulness score
was assigned.

HEAD: `65f49c1`.

DECISION: M1_PILOT_PARTIAL

## Current canonical delta — M1-03/C unjustified PARTIAL diagnosis

M1_03_C_FIRST_DIVERGENCE: Worker status parsing. The request was “Which
database queries need indexes?” and the selected Planning KB item was
`p-lite.database.v1`. Decomposition produced one independent task `T1`
(no dependencies); N retained it; task retrieval and O both selected
`src_1055b8f580d99531_c0000` and dropped nothing. The worker returned
`PARTIAL` with a valid citation but an empty `missing_information` list.

REQUEST: `Which database queries need indexes?`

GOLD_EXPECTED_OBLIGATIONS: Identify the corpus-supported indexing guidance;
do not invent specific unindexed queries or identifiers when the corpus does
not name them. Human correctness/faithfulness was not graded.

TASK_COVERAGE: One decomposed task `T1`, no dependency, selected evidence
`src_1055b8f580d99531_c0000`, O selected the same item and dropped none.

WORKER_TO_FINAL_STATUS: `app/research/worker.py` reads the model status at
line 50. `app/research/pipeline.py:213` deterministically aggregates any
non-`COMPLETE` task result into final `PARTIAL`; synthesis returns answer text
only and did not downgrade the status. The original C trace therefore has
worker `PARTIAL`, final `PARTIAL`, no final missing-information field, and no
status-reason field.

PARTIAL_CLASSIFICATION: **P7** — a reproducible status-contract/instrumentation
defect. The worker accepted a model-emitted `PARTIAL` without missing
information or a deterministic reason, then correctly preserved that status.

B_VS_C_COMPARISON: Both B/M1-03 and C/M1-03 decomposed one independent task
and selected the same database chunk; neither lost evidence through P/N/O. B
used its bounded user-request fallback and persisted two missing-information
items. C used its planning-guided task query directly, retained the same item
through O, but returned `PARTIAL` with no reason. The issue is not introduced
by O removing evidence; it is the worker status-output contract.

RECHECK_RUN_1: Immutable `m1-03-c-diagnosis-r1`, C/M1-03: `PARTIAL`, 3 LLM
calls, 41,240 ms, one `T1`, selected one evidence item, dropped none,
`missing_information=[]`, citation validity `1.0`, canonical rendered locator.

RECHECK_RUN_2: Immutable `m1-03-c-diagnosis-r2`, C/M1-03: `PARTIAL`, 3 LLM
calls, 31,502 ms, same one-task/evidence shape,
`missing_information=[]`, citation validity `1.0`, canonical rendered locator.

REPRODUCIBLE: YES — the original record and both immutable rechecks have the
same worker `PARTIAL` without a reason.

PIPELINE_DEFECT_REPRODUCED: YES, limited to the status-contract trace boundary;
it is not a decomposition, retrieval, P/N/O, citation, or synthesis defect.

CODE_CHANGE_REQUIRED: YES, and applied minimally. `TaskResult.status_reason`
now records `WORKER_PARTIAL_WITHOUT_REASON` when a worker returns `PARTIAL`
without missing-information. Status, task/evidence selection, prompts, model,
and P/N/O semantics are unchanged.

TESTS: Focused worker/pipeline regression `11 passed, 1 warning`; full pytest
`132 passed, 3 warnings` (the extra warning is the existing inaccessible
pytest cache; tests used an isolated repository basetemp).

FULL_M1_PILOT_READY: NO. The existing Fresh Phase 1 record is retained as
evidence; no live retry or new Phase 1 was started after this diagnosis.

BLOCKERS: Owner direction is required before any later fresh Phase 1 gate run.
No full pilot, M2, ablation, or human semantic grading was performed.

DECISION: M1_PILOT_PARTIAL
