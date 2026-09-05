# Repository governance

This repository is a local, research-oriented Multi-Agent RAG project. These
rules apply to agents and maintainers working in the repository.

## Decision boundaries

- `DETECTED` is not `APPROVED`. Use only framework references recorded in
  `.project/framework-ref.yaml`; an unavailable or uninspected framework is
  `UNCONFIRMED` and must not be copied, imported, or routed.
- Keep the research questions P (planning retrieval), N (task normalization),
  and O (overlap-aware context allocation) and the A/B/C comparison design.
  Do not invent new research scope.
- M0 permits A only; M1 permits A/B/C; M2 permits A/B/C/C-P/C-N/C-O. A
  condition/profile must be rejected when its implementation is unavailable;
  do not silently fall back.
- `qwen3:4b` is a calibration candidate, not a research-frozen model.

## Routing and safety

- Inference is local-only through the allowlisted Ollama adapter; FakeProvider
  is a test double and never semantic or milestone evidence.
- Workers are bounded by declared capability, scope, and exclusions. No
  self-modifying prompts, open-ended agent creation, browser/shell/code
  execution, paid/public providers, or external tool access are permitted.
- Preserve source/chunk provenance, citation validation, explicit
  `PARTIAL`/`NO_EVIDENCE`/failure states, immutable effective configuration,
  trace, canonical attempt ledger, and resource caps.
- Use the minimum sufficient context for the task. Read the governing profile,
  framework reference, and mutable state before broader repository context.

## Change control and approval

- `.project/project-profile.yaml` is stable routing configuration.
- `.project/framework-ref.yaml` records selected framework references only.
- `.project/project-state.yaml` records mutable milestone, runtime, and
  evaluation state.
- `docs/PROJECT_GOVERNANCE.md` is the human-readable policy and acceptance
  record.
- No agent may self-approve a milestone, convert plans/static/Fake evidence
  into semantic evidence, or mark a gate passed without the required evidence
  and human review. Preserve the last-known-good (LKG) path on scope cuts.
- Keep credentials out of client code, logs, commits, and artifacts. Do not
  modify production code as part of governance-only work unless separately
  authorized.

## Sprint delivery guidance

- Read `docs/NCKH_6_SPRINT_5_MEMBERS.md` whenever sprint or member ownership
  mapping matters, and read `docs/STUDENT_RESEARCH_CODE_STANDARD.md` for every
  coding task.
- Keep changes explicit, clean, student-readable, and narrowly scoped; avoid
  over-engineering.
- Report `INPUT`, `OUTPUT`, `FILES`, `TESTS`, `COMMIT`, and `BLOCKERS` when a
  task completes.
- When creating routine workers and the task API supports the choice, request
  `gpt-5.6-luna` with the highest available reasoning level.
