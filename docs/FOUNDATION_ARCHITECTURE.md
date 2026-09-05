# Foundation architecture

Status: approved foundation for the Local Multi-Agent RAG codebase. The
repository is currently an **M0 code candidate**; passing unit tests or using
the Fake provider does not promote a milestone.

## Design goals and invariants

- Local-first execution: inference is performed by the local Ollama adapter or
  by the Fake provider for deterministic wiring tests. No cloud inference is a
  CI or product dependency.
- One codebase with explicit implementation profiles and condition flags.
  Conditions must be selected before a run and recorded in its trace.
- Source scope, citation locators, token budgets, structured states, and
  failure/partial states are safety boundaries, not optional polish.
- Reproducibility artifacts identify the code commit, effective configuration,
  model, corpus/index version, and run attempt. A plan or a static test is not
  runtime evidence.

## Runtime shape

```text
Request
  -> condition/profile resolution
  -> Planning Retrieval (P, when enabled)
  -> task decomposition
  -> task normalization (N, when enabled)
  -> domain registry and assignment
  -> dependency validation and execution order
  -> task-specific retrieval
  -> Context Controller (O, when enabled)
  -> domain worker(s)
  -> structured task results
  -> synthesizer
  -> answer + validated source locators + trace/metrics
```

The current M0 path implements Vanilla RAG condition A. The code also contains
engineering wiring for later conditions behind the implementation profile; that
wiring is not evidence that M1 or M2 has been completed.

## Conditions and implementation boundaries

| Condition | Mechanism | Intended milestone |
| --- | --- | --- |
| A | Vanilla RAG; P, N, and O off | M0 baseline |
| B | LLM decomposition, task retrieval, and workers; P, N, and O off | M1 |
| C | P + N + O enabled with the multi-agent pipeline | M1 lite, M2 full |
| C-P | C without Planning Retrieval | M2 ablation |
| C-N | C without Task Normalization | M2 ablation |
| C-O | C without Context Controller | M2 ablation |

The condition table in `config/conditions.json` is the machine-readable source
for these flags. N/O-off conditions retain minimum schema, access, budget, and
citation guards.

### M0 — Technical MVP

M0 is the vertical slice from UTF-8 text ingestion and stable chunk IDs through
Vanilla RAG A, answer state, valid citation/source viewing, and basic trace and
metrics. The current repository is `M0 CODE CANDIDATE`; M0 becomes DONE only
after the target-laptop local-model gate, manual correctness/faithfulness
review, and restart/restore checks pass.

### M1 — Research MVP

M1 keeps A and adds runnable B/C on the same codebase, model, corpus, and
hardware. Its scoped implementation is P-lite, rules-only N, O-lite, structured
task execution, and a scored A/B/C pilot with trace and metrics. A Fake-provider
test can validate plumbing but cannot satisfy the pilot or local-model gate.

### M2 — Core complete

M2 is the frozen research protocol: full P/N/O, dependency-aware DAG execution,
all six conditions, frozen benchmark/config/corpus references, canonical
attempt accounting, main evaluation, ablations, statistics, and failure
analysis. `m2-test-ready` is a pre-test checkpoint, not M2 DONE. M3 extensions
are outside this foundation and may start only after M2 is stable.

## Evidence and rollback

Every promoted milestone needs a restorable Last Known Good (LKG), not just a
commit: compatible dependencies, model and corpus/index references, effective
configuration/hash, expected cases, raw trace/results, limitations, start and
restore instructions, and reviewer/date. Failed, missing, or unsupported runs
remain visible in the ledger and are not silently replaced.

## Explicit non-goals

This foundation does not add a cloud provider, deployment workflow, a new
research module, a semantic-quality claim, or a requirement to use a particular
vector database. Implementation work must remain within the active milestone
and its approved scope.
