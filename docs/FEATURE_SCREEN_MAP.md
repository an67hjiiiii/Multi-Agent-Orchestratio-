# Product Baseline v4 — P0 Feature / Screen Map

**Status:** documentation/state contract for anti-QA review; no screen or
frontend implementation is authorized by this file.

## P0 surfaces

The product is one answer-first workspace with contextual panels. A “screen”
below is a user-addressable surface, not a new backend route or persisted
workspace entity.

| Screen ID | Surface | Primary job | Entry / exit | P0 states and data |
| --- | --- | --- | --- | --- |
| S00 | Local auth | Register, sign in, restore, or end a local session. | App start; successful auth enters S01; sign out returns here. | loading, invalid credentials, duplicate account, session expired; no password/token display. |
| S01 | Workspace / readiness | Establish local runtime, corpus scope, and available capabilities. | App start; retry affected bootstrap area. | `BOOTING`, `OFFLINE`, `DEGRADED`, `READY_EMPTY`, `READY`; health/config/KB status. |
| S02 | Corpus / source import | Add a bounded local source and see its durable result. | S01 or answer → Add source; return to source list/answer. | `idle`, `uploading`, `indexing`, fulfilled, error; source list and snapshot. |
| S03 | Source / chunk context | Inspect canonical provenance and readable support text. | S02 or valid citation → source/chunk; Back returns to origin. | source/chunk loading, available, 404/unavailable; no fabricated offsets/highlights. |
| S04 | Answer / run canvas | Ask, read, and recover from one immutable run. | S01/New question → submit; terminal result or safe request error. | pending request; `COMPLETE`, `PARTIAL`, `NO_EVIDENCE`, `FAILED`, unknown. |
| S05 | Evidence / run inspector | Inspect returned evidence, citation audit, trace, and metrics. | S04 citation/Inspect evidence; close restores origin focus. | context first; valid/invalid citation split; raw events/metrics when returned. |
| S06 | Recent runs / reopen | Find and reopen an individual persisted run. | Workspace history; select `run_id`; return to S04/S05. | loading, list, empty-after-success, scoped error; no replay or mutation. |
| S07 | Research / plan inspector | Disclose returned identity and planning-only detail when allowed. | S05 or explicit Research/Demo action. | condition/profile/provider/model/config, P-lite plan/warnings; unavailable is explicit. |
| S08 | Settings / minimal admin | Show local account/runtime settings and bounded admin status/users. | S01 account menu; admin controls only for ADMIN. | settings load/error; unauthorized admin is blocked; no secrets or self-elevation. |

## Feature-to-surface map

| Feature ID | P0 module | Primary surface(s) | Backend seam(s) | Acceptance focus |
| --- | --- | --- | --- | --- |
| F-P0-01 | P0-M01 Workspace and readiness | S01 | `GET /api/health`, `/api/config`, `/api/kb/status`, `/api/local-model/health` | Read capability; distinguish runtime/corpus readiness from run status. |
| F-P0-02 | P0-M02 Corpus and sources | S02, S03 | `GET /api/sources`, `/api/sources/{source_id}`, import endpoints | Additive bounded import; preserve source/chunk/snapshot identity. |
| F-P0-03 | P0-M03 Ask and run | S04 | `POST /api/chat` | Non-blank request; one request binds to one returned run; no silent fallback. |
| F-P0-04 | P0-M04 Answer and evidence | S04, S05, S03 | `RunRecord.task_results`, `GET /api/chunks/{chunk_id}` | Answer first; validated canonical citations; honest partial/no-evidence/error states. |
| F-P0-05 | P0-M05 History and reopen | S06, S04 | `GET /api/runs`, `/api/runs/{run_id}` | Reopen exact immutable record; history failure is not empty history. |
| F-P0-06 | P0-M06 Research inspector | S05, S07 | returned run `events`/`metrics`; `POST /api/tasks/decompose` | Progressive disclosure; planning IDs never become answer citations. |
| F-P0-07 | P0-M07 Local auth and session | S00 | `POST /api/auth/register`, `/api/auth/login`, `/api/auth/logout`, `GET /api/auth/session` | Local-only session persistence, hashed credentials/tokens, USER/ADMIN identity. |
| F-P0-08 | P0-M08 Settings and admin | S08, S05, S06 | `GET /api/settings`, `/api/admin/status`, `/api/admin/users`, `/api/runs/{run_id}/trace`, `/api/runs/{run_id}/evidence`, `GET /api/history` | Safe settings/admin/inspection payloads; server-side role boundary and immutable run access. |

## Critical paths

```text
S00 ──local session──▶ S01 ──Add source──▶ S02 ──source ready──▶ S04
S01 ──New question──▶ S04 ──terminal result──▶ S05 ──citation──▶ S03
S04 ──Recent runs──▶ S06 ──open run──▶ S04
S05 ──Research/Demo──▶ S07 ──back/close──▶ S04 or S05
```

Alternate paths preserve the same identities:

- `PARTIAL` keeps the answer and exposes missing information;
  `NO_EVIDENCE` says that no answer-domain support was validated; `FAILED`
  remains an execution/request failure.
- A chunk/source lookup error is local to inspection and does not rewrite the
  run status. A network/API error is not `NO_EVIDENCE`.
- A plan inspection is optional, bounded, and does not create a run, spawned
  agent, or answer citation.

## Deliberately absent P0 surfaces

There is no conversation/thread view, cross-run comparison/winner, agent
registry, P/N/O toggle, source delete/replace/undo, cancellation/background
retry, cloud provider, external identity provider, quality score, or milestone
approval screen. A future capability requires a separately reviewed contract.

## Anti-QA screen checks

The implementation handoff should verify at least one route through each
surface at desktop and narrow/mobile widths: keyboard-reachable auth/composer and
history, visible focus, labelled drawers/sheets, citation-to-context and
return focus, distinct loading/empty/error states, and preserved answer context
after an inspector failure. Auth/session expiry and role denial must be checked
separately. This is a checklist for later QA, not evidence that those checks
have passed.
