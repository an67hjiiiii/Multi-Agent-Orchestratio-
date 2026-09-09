# Research alignment check — RQ, metric, and evaluator freeze

**Scope:** `RESEARCH_ALIGNMENT_ONLY` (static/evaluator-only). No Ollama,
benchmark, M1/M2 run, dataset mutation, model change, or core-pipeline change
was performed.

## Freeze boundary

- Audit HEAD: `17bd23ad2733e176fa065f7b50f56fcd97e44108`.
- Canonical mutable state: `.project/project-state.yaml`.
- State currently records the 15-case development/validation subset as human
  approved, while the 30-group final packet is still pending approval.
- `datasets/final/final_benchmark_v1.json` has
  `status=FROZEN_PENDING_HUMAN_APPROVAL`.
- `datasets/final/final_gold_v1.json` has `status=PENDING_HUMAN_APPROVAL`;
  every scenario row remains `PENDING_HUMAN_APPROVAL`.
- The final runner therefore remains launch-blocked until the final packet is
  approved. This is not inferred from file presence.

## Research problem and positioning

The primary problem is reliable handling of complex, multi-obligation requests:
turning one request into distinct obligations, assigning bounded specialized
work, retrieving evidence per task, preserving legitimate shared evidence, and
reporting quality/coverage together with token and latency cost. P, N, and O
are controlled mechanisms in that pipeline, not standalone novelty claims.

`LOCAL_POSITIONING: SECONDARY`. Local Ollama execution is the reproducible
deployment/evaluation setting and resource constraint; it is not presented as
the primary research contribution.

The existing plan already uses cautious contribution language (reproducible
pipeline, bounded task/context selection, transparent benchmark, and empirical
ablation). It does not claim that combining known mechanisms is novel, does
not claim online learning, and defines an adaptive graph as request-dependent
task/role/context allocation. No novelty over-claim requires a source edit.

## Operational RQ map for the final six-condition report

The following is an analysis/reporting map requested for the final experiment.
It does not change the implementation or silently replace the plan's original
registered labels. The current `RESEARCH_PLAN_v1.1.md` registers RQ1/RQ2 as
the primary contrasts (C vs C-P and C vs C-O) and RQ3 as the system-level view;
the A/B, N, O, and integrated views below are explicit operational lenses.

| Lens | Comparison | Required evidence and bounded interpretation |
|---|---|---|
| RQ1 | C vs C-P; B vs C is supporting context | Planning/decomposition success, gold-obligation coverage, missing/required obligations, task count, and planning trace. No causal claim from task self-reports. |
| RQ2 | A vs B | Decomposition-enabled path versus Vanilla RAG on answer quality/grounding, obligation coverage, citation validity, and terminal status. A has no task-plan metrics; use `N/A`, not a zero. |
| RQ3 | C vs C-N | Tasks before/after, merge/removal decisions, obligation preservation, dependency validity, and answer/grounding outcomes. Only exact/approved normalization behavior is compared. |
| RQ4 | C vs C-O | Retrieved/selected/dropped evidence, drop reasons, context tokens, shared/reused evidence, and quality/grounding. Legitimate shared evidence is not treated as an error. |
| RQ5 | A vs B and B vs C | Integrated quality/status/grounding/citation, coverage, tokens, latency, and failure/partial rates. It is a system comparison, not proof that one mechanism caused every difference. |
| RQ6 (optional) | Local deployment view | Local-only feasibility, latency, memory, and failure boundaries; secondary to the research questions and not a novelty claim. |

## Metric-to-source matrix

`SUPPORTED` means a source field or deterministic evaluator already exists;
`ADDED` means the evaluator-only adapter added in this alignment delta exposes
the value after terminal inference; `MISSING` means no safe scorer/annotation
is present and the result must remain unavailable or human-owned.

| Metric | Source field/function | Conditions | RQ | Status | Boundary |
|---|---|---|---|---|---|
| Terminal status / failure | `row.status`, `events.run_failed`, `failure_stage` | A/B/C/C-P/C-N/C-O | all | SUPPORTED | Includes `COMPLETE`, `PARTIAL`, `NO_EVIDENCE`, and `FAILED`; failures are not dropped. |
| Task count / task IDs | `row.tasks` | B/C/ablations; A is `N/A` as a mechanism metric | RQ1/RQ3/RQ5 | SUPPORTED | Structural count only; not task correctness. |
| Required/covered/missing obligations | decomposition trace fields; `calculate_task_coverage()` with independent task-match annotations | B/C/ablations | RQ1/RQ3/RQ5 | SUPPORTED | Current final gold has answer points but no independent obligation-ID/task-match packet; value is `UNDEFINED` until supplied. |
| Candidate evidence Recall@K | `vanilla_retrieval.candidates` or `task_retrieval.candidates` joined to frozen gold after inference | all where evidence gold exists | RQ1/RQ2/RQ4/RQ5 | ADDED | ID-level retrieval recall; alternate evidence groups and semantic entailment still require annotation. |
| Selected-evidence recall | `selected` task/vanilla trace joined to gold | all where evidence gold exists | RQ4/RQ5 | ADDED | Separates retriever recall from O/context selection; does not score answer truth. |
| Role assignment accuracy | `Task.domain` plus gold expected roles | B/C/ablations | RQ1/RQ2/RQ3/RQ5 | MISSING | No independent obligation-to-role annotation/scorer; keep `N/A`/pending. |
| Duplicate task removal | `metric_snapshot.duplicate_tasks_removed`, `duplicate_task_rate` from normalization trace | N-on conditions (`C`, `C-P`, `C-O`) | RQ3 | SUPPORTED | Runtime structural removal only; research redundant-task rate needs human/independent annotation. |
| Context/token reduction | `context_tokens_est`, `total_tokens`, per-task `context_tokens`, selected/dropped evidence | all; compare O-on/O-off | RQ4/RQ5 | SUPPORTED | Report quality beside cost; lower tokens alone is not success. |
| Shared/reused evidence | `shared_evidence_ids`, `reused_from_task_ids`, `overlap_summary` | O-on; O-off is explicitly `N/A` | RQ4 | SUPPORTED | Shared evidence is retained when needed; raw overlap is descriptive, not an error. |
| Drop decisions/reasons | `task_retrieval.dropped`, `selected_evidence.reason` | O-on/O-off | RQ4 | SUPPORTED | Reasons are structural (`low_relevance`, budget, overlap, etc.); semantic necessity remains review-owned. |
| Citation validity / locator | `citations_valid`, `citations_emitted`, `citation_locator_validity` | all evidence-bearing rows | RQ2/RQ4/RQ5 | SUPPORTED | Valid locator/ID is not semantic faithfulness. |
| Evidence grounding / faithfulness | Human rubric; no automated scorer in final runner | all | RQ2/RQ4/RQ5 | MISSING | Must remain `PENDING_HUMAN_REVIEW`; never infer from citation presence. |
| Expected answer-point quality | gold `expected_answer_points` + blinded human rubric | all | RQ2/RQ5 | MISSING | Gold is available only after inference; no self-grading or text-overlap shortcut. |
| Expected missing-information behavior | gold `expected_missing_information`, terminal status, task result missing info | all, especially intentional missing cases | RQ2/RQ5 | ADDED | Adapter exposes gold and observed missing fields; semantic adequacy remains human-owned. |
| Dependency semantics | `tasks[].depends_on`, graph validity, gold `dependency_expectation` | dependency strata | RQ1/RQ3/RQ5 | ADDED | Acyclic/known-edge structure is automatic; whether an edge is semantically required remains human/annotation-owned. |
| N expectation | normalization trace + gold `normalization_expectation` | N-on/N-off contrasts | RQ3 | ADDED | Adapter exposes MERGE/KEEP/ROLLBACK evidence; no semantic merge is auto-approved. |
| O expectation | task retrieval/overlap trace + gold `overlap_expectation` | O-on/O-off contrasts | RQ4 | ADDED | Adapter exposes shared/selected/dropped IDs and reasons; necessity is not inferred from cosine or overlap alone. |
| LLM calls / input/output/total tokens | `RunMetrics` and `metric_snapshot` | all | RQ5/RQ6 | SUPPORTED | `retry_count` remains `NOT_RECORDED`; do not replace with zero. |
| Latency | `latency_ms`, retrieval/generation latency | all | RQ5/RQ6 | SUPPORTED | E2E includes pipeline work represented by the run; report p50/p95 only when enough terminal rows exist. |
| RAM / VRAM | `peak_rss_mb`, `gpu_memory_mb` | all where runtime reports it | RQ6 | SUPPORTED | Missing values remain `N/A`. |

High-value summaries are therefore permitted only when their denominators are
present: obligation coverage rate, annotation-backed redundant-task reduction,
and context/token reduction paired with answer quality/grounding. A lower cost
with a quality/coverage drop must not be called an improvement.

## Evaluator and gold isolation

The runner/evaluator boundary is now explicit:

1. `load_cases()` flattens only `case_id`, request, and kind and rejects
   gold-shaped fields.
2. `run_final_experiment()` receives no gold loader and persists only
   request/runtime/trace/metric data.
3. `evaluate_after_inference()` verifies every row is terminal before the first
   gold load.
4. `app/evaluation/scenario_evaluator.py` now maps frozen request variants to
   scenario gold only after that terminal check. It exposes expected status,
   answer points, missing-information, dependency/N/O expectations, candidate
   and selected evidence recall, graph validity, citation locator validity, and
   condition-trace checks in an evaluator-facing row.
5. Semantic answer points, role assignment, dependency meaning, normalization
   meaning, overlap necessity, answer quality, and faithfulness stay
   `PENDING_HUMAN_REVIEW`. Optional independent task-match annotations are
   passed to the existing deterministic `calculate_task_coverage()` function;
   no obligation IDs are invented from answer prose.

This is the smallest evaluation-only addition needed to use scenario gold
without inserting gold into generation. It does not alter P/N/O, decomposer,
retrieval, worker, synthesizer, model, provider, or dataset semantics.

## Condition fairness

The declared condition table is unchanged:

- A: Vanilla RAG; P/N/O off and no decomposition-stage mechanism metric.
- B: LLM decomposition plus task-specific retrieval; P/N/O off.
- C: P/N/O on; planning retrieval precedes decomposition, normalization is
  traced, and O emits task-level allocation/overlap trace.
- C-P, C-N, C-O: one registered flag is removed at a time while model,
  corpus, request, budgets, provider, and evaluator remain shared.

The adapter checks actual `run_started.flags` (falling back to effective config)
and observed stages, rather than trusting condition labels. Mechanism-specific
metrics for A are `N/A`, not zero-filled. Gold is never used to alter a
condition or to select a favorable run.

## Validation performed (no live provider)

- `tests/test_scenario_evaluator.py`, `tests/test_task_coverage.py`, and
  `tests/test_pilot_ledger.py`: **17 passed**.
- `py_compile app/evaluation/scenario_evaluator.py`: **PASS**.
- Static case↔gold/evidence mapping: **PASS** (120 variants → 30 scenario
  rows; 3 referenced frozen evidence IDs resolve).
- `git diff --check`: **PASS** (pre-existing CRLF normalization warnings only).
- A broader legacy focused command also ran once and had one pre-existing
  failure: `tests/test_final_experiment_runner.py::test_canonical_final_manifest_flattens_request_variants_only`
  still expects the old M1F-S01 request text, while the already-dirty frozen
  dataset contains the revised request. No dataset or test was changed for
  that failure.
- Ollama/model runs: **0**. No M1/M2/720-run or benchmark execution.

## Alignment status

| Boundary | Result |
|---|---|
| Research problem and local positioning | ALIGNED; local is secondary. |
| P/N/O and A/B/C contracts | ALIGNED with existing condition table and traces. |
| Runtime telemetry and efficiency metrics | SUPPORTED. |
| Scenario-level gold join and evidence-recall/structural adapter | ADDED, post-inference only. |
| Semantic answer/faithfulness/role/dependency/N/O judgments | PENDING HUMAN REVIEW by design. |
| Final dataset/gold approval and launch authorization | PENDING; current files are not launch-approved. |

`READY_TO_FREEZE_AND_RUN_FINAL_EXPERIMENT: NO` until the final dataset/gold
approval state is reconciled and the human semantic evaluator supplies the
required annotations/scores. This report does not approve gold or a milestone.

## Change boundary

- `MODEL_CHANGED: NO`
- `CORE_PIPELINE_CHANGED: NO`
- `FINAL_DATASET_SEMANTICS_CHANGED: NO`
- `OLLAMA_RUNS: 0`
- `TERRA_USED: 0`
- `SOL_USED: 0`
- `ASTRA_USED: 0`

### Files changed by this alignment delta

- `app/evaluation/scenario_evaluator.py` — evaluator-only post-inference
  scenario join and structural metric adapter.
- `tests/test_scenario_evaluator.py` — focused isolation/recall/trace tests.
- `reports/final_experiment/research_alignment.md` — this freeze artifact.

Unrelated pre-existing dataset, report, raw-run, and review artifacts remain
untouched and unstaged.

## Decision

`RESEARCH_ALIGNMENT_PARTIAL`

The research framing and runtime metric boundaries are aligned, and the
scenario-level post-inference join is available. The final experiment is not
yet ready to run because semantic answer/faithfulness/role annotations remain
human-owned and the final 30-group dataset/gold files still report pending
approval. No experiment or approval was inferred.
