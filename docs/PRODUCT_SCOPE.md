# Product Baseline v4 — P0 Product Scope

**Status:** implementation/state contract; implementation is ready for owner
and anti-QA review. It is not semantic evidence or milestone approval.

## Product boundary

The product is a local evidence desk: a user adds a bounded local corpus,
asks one question, reads a bounded answer, and follows validated citations to
the source/chunk that supports the answer. The answer is the primary task;
research detail is progressive disclosure in an explicit Research/Demo view.

P0 owns the user-visible workflow, honest runtime states, provenance display,
and safe recovery. It does not promise semantic correctness, faithfulness,
quality scores, or research-milestone completion.

## P0 modules

| ID | Module | P0 responsibility | Hard boundary |
| --- | --- | --- | --- |
| P0-M01 | Workspace and readiness | Bootstrap health/config, local runtime, corpus readiness, and the active scope. | Read returned capability; do not invent conditions or provider fallbacks. |
| P0-M02 | Corpus and sources | Import bounded UTF-8 text/code/Markdown, list sources, and inspect canonical chunks. | Import is additive and does not create a run; preserve source/chunk provenance. |
| P0-M03 | Ask and run | Submit one non-blank request and bind it to one returned persisted run. | A request is not a run; retry creates a new run with explicit condition/provider. |
| P0-M04 | Answer and evidence | Lead with the answer, terminal state, missing information, and validated citations. | `COMPLETE` is not correctness; invalid locators and planning evidence are not answer citations. |
| P0-M05 | History and reopen | List and reopen individual persisted runs without replay or mutation. | History is a flat immutable run list, not a conversation/thread product. |
| P0-M06 | Research inspector | Disclose returned identity, trace, metrics, citation audit, and permitted P-lite planning detail. | Inspection does not self-approve quality, a gate, or a milestone; planning is not answer evidence. |
| P0-M07 | Local auth and session | Register, sign in, persist a local session, and sign out with USER/ADMIN boundaries. | Store only password/token hashes; no hosted identity, secret echo, or client-side role elevation. |
| P0-M08 | Settings and admin | Show safe local settings and a minimal read-only admin surface for ADMIN accounts. | Do not expose secrets; regular users cannot self-elevate; admin endpoints remain server-authorized. |

## Core user flow

1. **Enter locally.** Register or sign in to a local account; restore a valid
   session on reload and keep credentials on this machine.
2. **Open workspace.** Read health, config, corpus status, sources, and recent
   runs. Show `BOOTING`, `OFFLINE`/`DEGRADED`, `READY_EMPTY`, or `READY` as
   applicable.
3. **Prepare evidence.** Add a local accepted source. Show import/index
   progress and the resulting source, chunk count, and snapshot when returned.
4. **Ask.** Enter a non-blank question against the active local corpus and
   submit it with the capability-returned condition/provider boundary.
5. **Read the run.** Keep the submitted question with one returned `RunRecord`.
   Render `COMPLETE`, `PARTIAL`, `NO_EVIDENCE`, `FAILED`, or an unknown status
   without coercion.
6. **Verify support.** Open a valid canonical citation to its chunk/source
   context, then return to the same answer and focus origin. Invalid or missing
   locators remain non-linking and visible as such.
7. **Recover honestly.** For partial/no-evidence results, show what is missing
   and offer a bounded next action such as refine or add source. For failures,
   keep the request and use only a safe, explicit retry; do not relabel an API
   or inspection error as `NO_EVIDENCE`.
8. **Reopen or inspect.** Select a prior run without rerunning it. Research/Demo
   may reveal returned technical detail and planning-only output when the
   active profile permits it.

## Research and product boundary

The research contract remains unchanged:

- **P** is Retrieval-Guided Task Decomposition: planning retrieval precedes
  decomposition when P is enabled.
- **N** is conservative Task Normalization: merge only exact canonical
  duplicates and preserve distinct obligations/dependencies.
- **O** is Overlap-Aware Context Allocation: preserve legitimate shared
  evidence and remove only unnecessary repetition.
- **A** is Vanilla RAG with P/N/O off; **B** is decomposition plus
  task-specific retrieval; **C** is multi-agent P+N+O. Conditions and profiles
  are capability-controlled and never silently substituted.
- M0 permits **A** only; M1 permits **A/B/C**; M2 permits **A/B/C/C-P/C-N/C-O**.
  The current mutable milestone/evaluation values remain authoritative in
  `.project/project-state.yaml`; this product contract does not promote them.
- Inference is local-only through the allowlisted Ollama adapter. `FakeProvider`
  is wiring/test-only and is never semantic or milestone evidence.

The P0 product may display returned condition/profile, P-lite planning, N/O
metrics, traces, and configuration, but it must not change P/N/O semantics,
enable unavailable conditions, expose a new research module, or infer approval
from a screen, static check, unit test, or FakeProvider run. `qwen3:4b` remains
a calibration candidate, not a research-frozen model.

## Explicitly out of scope

- New or redesigned research methods, conditions, ablations, prompts, models,
  providers, datasets, gold answers, rubrics, or evaluation protocol.
- Cloud/public inference, external worker tools, credentials in client code,
  external identity providers, source deletion/replacement, cancellation,
  background retries, sharing, or a comparison winner/quality score.
- Agent lifecycle controls, conversation threads, claim offsets/highlights not
  returned by the backend, or a broad analytics/dashboard product.
- Any dataset/gold, research report/run artifact, milestone promotion, or push
  as part of the product implementation. Code commits remain bounded to the
  explicitly authorized P0 milestone.

## Anti-QA handoff expectations

This baseline is a contract handoff, not a QA result. Before P0 acceptance,
the owner/QA reviewer should check the actual implementation against
`FEATURE_SCREEN_MAP.md`, `SYSTEM_CONTRACT.md`, and this scope:

- bootstrap and corpus readiness remain distinct from run status;
- source import, question, run identity, history, and citation-to-chunk return
  paths work without silent fallback or mutation;
- `COMPLETE`, `PARTIAL`, `NO_EVIDENCE`, `FAILED`, unknown statuses, and API /
  resource errors remain distinguishable and recoverable;
- active conditions/provider/model/config are read from the returned contract;
  planning evidence stays separate from answer evidence;
- Normal is answer-first, while Research/Demo is progressive disclosure and
  does not change the run/configuration;
- responsive/keyboard paths keep corpus, history, evidence, and recovery
  reachable.
- auth loading/error/session-expiry paths are local and distinguishable;
  settings and admin surfaces do not expose secrets or permit self-elevation.

Those checks may produce implementation or live QA evidence later. They do not
alter the state contract or promote M0/M1/M2; failed checks remain evidence and
must be handed back with the affected trace/record intact.
