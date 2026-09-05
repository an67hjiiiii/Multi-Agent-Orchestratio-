# Project Governance

**Status:** governance profile for human review; not a milestone approval.

## Authority and scope

The research design remains P (planning retrieval), N (task normalization),
and O (overlap-aware context allocation), evaluated through the declared
conditions. This governance layer adds routing and acceptance rules only; it
does not redesign the research or add modules.

Terra’s M-1 analysis is the source for framework status. `D:\AI-Framework`
had no inspectable inventory in that analysis, so it is `UNCONFIRMED`. No
framework component is selected, copied, imported, or routable. A future
framework reference requires an inspectable source and human review.

## Stable routing contract

| Boundary | Contract |
| --- | --- |
| Inference | Local-only Ollama adapter; FakeProvider is a test double. No paid/public provider or external worker tools. |
| Conditions | M0: A only. M1: A/B/C. M2: A/B/C/C-P/C-N/C-O. |
| Implementation | M1 uses P-lite/N-rules/O-lite when enabled; M2 is full P/N/O. Unavailable implementations are rejected; no silent fallback. |
| Model | `qwen3:4b` is a calibration candidate and is not research-frozen. |
| Execution | Bounded context/run/retry budgets; default local generation concurrency is 1. |
| Evidence | Preserve source/chunk provenance, citation/location checks, trace, immutable effective config, terminal failures, and the canonical attempt ledger. |

The machine-readable stable contract is
`.project/project-profile.yaml`. The framework reference register is
`.project/framework-ref.yaml`; mutable milestone/runtime/evaluation state is
`.project/project-state.yaml`.

## Governance acceptance gates

Governance review may accept this configuration only when the ownership tracks
provide clean pre-flight, an explicit contract, appropriate tests, a
secret/noise check, and isolated commits. Governance does not certify those
tracks or approve itself.

Milestone claims require the research-plan gates and their evidence. In
particular, plans, static checks, UI screens, unit tests, and FakeProvider
results are wiring evidence only; they do not prove semantic quality or M0,
M1, or M2 completion. A claim must state the exact code/config/corpus/model
references, condition and implementation profile, raw traces/attempts, review
status, and limitations.

## Scope-cut and rollback rules

Extensions and advanced UI are cut before the core research path. Dataset,
rubric, evaluation, trace, and LKG are never removed to meet a schedule. A
cut must record owner, reason, date, changed module/flag, affected claim, and
rollback/LKG. Keep access control, token caps, schema validation, and citation
integrity enabled in every condition.

## Approval record

Current state is recorded in `.project/project-state.yaml`. Human review,
milestone promotion, and framework selection remain pending; no agent may
self-approve any of them.
