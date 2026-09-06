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
