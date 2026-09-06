# Sprint 3 P-lite pilot

## Purpose and boundary

This pilot is a small structural check for Sprint 3 P-lite: bounded planning
retrieval followed by structured task decomposition. It is not a correctness
benchmark, a final-answer evaluation, or an M0 approval artifact.

The case list is frozen in
`datasets/planning/p_lite_pilot_cases.json`. The cases intentionally contain
requests whose expected output can be checked as a task-graph shape. They do
not contain final answers, answer-domain evidence, gold task titles, or
semantic obligation annotations.

The pilot remains inside the locked Sprint 3 boundary:

- inference is local-only through the existing Ollama adapter;
- FakeProvider is permitted for wiring and contract tests only, never for
  semantic or milestone evidence;
- P-lite may retrieve bounded planning context and make one structured retry;
- N normalization, O context allocation, a DAG scheduler, parallel execution,
  and a Human Review UI redesign are out of scope;
- M0 remains `TECHNICAL_PASS` with
  `HUMAN_REVIEW_PENDING`; this document cannot approve that gate.

No live calibration is run as part of this artifact. A real local run requires
the target-laptop Ollama gate and the required human review separately.

## Case inventory

| Case | Shape under test | Structural constraint | Planning-evidence expectation |
| --- | --- | --- | --- |
| `PLITE-01` | One task | Exactly one task, zero edges, acyclic | At least one bounded planning item ID |
| `PLITE-02` | Chained | Two tasks, one dependency edge, chain depth two, acyclic | At least one bounded planning item ID |
| `PLITE-03` | Partially independent | A two-task chain plus one isolated task; three tasks, one edge, two components | At least one bounded planning item ID |
| `PLITE-04` | Ambiguous request | One to three tasks; valid acyclic graph; zero to two edges | Zero or more IDs; preserve the observed outcome |
| `PLITE-05` | Weak/no planning evidence | One to two tasks; valid acyclic graph; zero to one edge | Zero IDs or bounded fallback IDs |

The graph shapes constrain structure, not whether a task is substantively the
right answer to the request. The ambiguous and weak-evidence cases therefore
use ranges and require the observed warning/evidence state to be recorded;
they must not be repaired by inventing a hidden expected task list.

## Required per-run record

Each attempt must be bound to a case ID and retain the following identity
fields together: `run_id`, `case_id`, `created_at`, `provider`, `model`,
`config_hash`, `effective_config`, and terminal `status`. Keep the immutable
effective configuration and the trace with the result so that a later review
can distinguish a structural contract check from a semantic run.

### Terminal state

Record one terminal state exactly as emitted by the run: `COMPLETE`, `PARTIAL`,
`NO_EVIDENCE`, or `FAILED`. Do not turn a missing planning item into a
successful evidence claim, and do not convert an exception into a partial
success. If a run stops before decomposition, record the failure stage and
retain the zero-call/zero-evidence values rather than fabricating them.

### Planning evidence IDs

Capture both sides of the locked contract when available:

1. `PlanningRetrievalResult.item_ids` in retrieval order; and
2. `DecompositionResult.planning_evidence_ids` after the decomposer has bound
   the evidence used for planning.

IDs must be stable `PlanningKnowledgeItem.id` values, unique at the
decomposition boundary, and capped at the configured planning top-k (three in
this pilot contract). Planning evidence is guidance for decomposition, not
answer-domain evidence. If a later end-to-end slice emits source/citation IDs,
store those in their own field and never merge the two namespaces.

For `PLITE-05`, zero planning IDs is an allowed observation. A bounded fallback
item is also allowed if the retriever reports that fallback explicitly; it must
not be described as a relevant match merely because an ID exists.

### Latency

Record latency in integer milliseconds using a monotonic clock. The required
fields are:

- `metrics.latency_ms`: from `run_started` through the terminal state;
- `metrics.retrieval_latency_ms`: time spent in retrieval calls; and
- `metrics.generation_latency_ms`: time spent around local model calls.

If a stage was not reached or a measurement is unavailable, use `null` plus a
reason. Do not replace unavailable measurements with zero and do not compare
latency across runs with different model, hardware, corpus, or effective
configuration bindings.

### LLM-call count

Count one provider result as one LLM call and record the count in
`metrics.llm_calls`. For the decomposition slice, the normal budget is one
call with at most one structured retry, so the upper bound is two calls. Keep a
stage breakdown when the harness includes more than decomposition; do not
hide worker or synthesis calls inside the decomposition count. A provider or
infrastructure failure must not trigger unbounded retries.

### Dependency validity

Validate every returned task graph before evaluating its shape:

- task IDs are unique;
- every dependency refers to a returned task ID;
- a task cannot depend on itself; and
- the graph is acyclic.

An invalid graph is a rejected structured output, not a valid zero-edge graph.
Do not silently remove an unknown dependency or break a cycle to make a case
pass. Record the validation result and the failure reason alongside the
terminal state.

## Task Coverage collection

Task Coverage is normally the number of approved task obligations served by at
least one task divided by the number of approved obligations. This structural
pilot deliberately has no approved obligation annotations, so its value is
`NOT_SCORED`/not applicable. The run record must still include:

```json
{
  "status": "NOT_SCORED",
  "numerator": null,
  "denominator": null,
  "definition_version": "not-applicable",
  "reason": "No approved obligation annotations in the structural-only pilot."
}
```

Do not infer Task Coverage from task count, task IDs, exact titles, model
self-reports, or the presence of planning evidence. If a separately approved
annotation set is introduced later, record its version and case binding before
computing the metric; that future semantic evaluation is outside this
dataset/document change.

## Interpretation and evidence boundary

The focused test for this artifact checks JSON shape, case coverage, graph
constraints, evidence-ID rules, and the explicit non-scoring boundary. It does
not call Ollama or claim that a planner produced semantically correct tasks.
FakeProvider results are wiring evidence only. A passing structural test is
therefore `P-lite contract ready for review`, not `P-lite semantic PASS`,
`M0 DONE`, or `M1 DONE`.
