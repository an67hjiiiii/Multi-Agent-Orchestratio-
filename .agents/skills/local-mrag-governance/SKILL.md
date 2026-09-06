---
name: local-mrag-governance
description: Apply the Local Multi-Agent RAG research contract when work involves A/B/C, P/N/O, retrieval, decomposition, context allocation, traces, pilots, evaluation, or milestones.
version: 1.0.0
---

# Local Multi-Agent RAG governance

## Trigger

Use this skill for pipeline A/B/C, P/N/O, retrieval, decomposition, context
allocation, trace, evaluation, pilot, or milestone work.

## Source of truth

Read `.project/project-state.yaml` before wider project context. It is the
canonical mutable state; a report does not override it. Preserve
`.project/project-profile.yaml` and `.project/framework-ref.yaml` as their
defined routing and framework-reference records.

## Research contract

- P is Retrieval-Guided Task Decomposition. When P is on, planning retrieval
  occurs before decomposition.
- N is conservative Task Normalization: merge only exact canonical duplicates;
  preserve distinct obligations and valid dependencies.
- O is Overlap-Aware Context Allocation: preserve legitimate shared evidence;
  identify unnecessary repetition without removing evidence needed by a task.
- A is Vanilla RAG; B is decomposition plus task-specific retrieval; C is
  P+N+O. Verify real trace behavior, not only labels or config names.
- Keep A/B/C comparable. Do not change model, provider, prompt budget, test
  cases, gold data, or methodology merely to pass a gate.

## Runtime, evidence, and reporting

- Use local-only allowlisted Ollama inference; never fall back to cloud.
- Do not leak gold/expected answers into retrieval, prompts, worker context,
  or evaluation inputs.
- Preserve provenance, immutable effective configuration, traces, canonical
  attempt ledger, citations, resource caps, and explicit COMPLETE/PARTIAL/
  NO_EVIDENCE/failure states. A failed run remains evidence.
- For completed scoped work, report INPUT, OUTPUT, FILES, TESTS, COMMIT, HEAD,
  TRACE/live-run evidence where applicable, and BLOCKERS. Do not call
  FakeProvider/static evidence semantic or milestone proof.
- Keep changes small, readable, traced, tested, and compatible with the
  last-known-good path.

## Orchestration

- Reuse an appropriate existing task/worktree. Send delta context, not full
  project history. Allow one production writer per wave.
- Parallelize only independent work. GPU/model runs are serial. Terra handles
  integration. Escalate to Sol only for an actual contract, architecture, or
  root-cause defect; do not use it as a default worker.

## Hard stops

- Do not begin full M1, M2, ablations, a new methodology, gold-data changes,
  cloud inference, push, destructive cleanup, or unrelated refactors without
  explicit owner authorization.
- Do not self-approve milestones or convert plans, FakeProvider checks, or
  static checks into empirical/live evidence.
- If state, trace, allowed condition, provenance, or scope conflicts, stop at
  the first divergence and report the exact blocker instead of bypassing it.
