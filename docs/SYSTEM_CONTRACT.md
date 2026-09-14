# Product Baseline v4 — P0 System Contract

**Status:** implementation-facing contract for anti-QA review. It records the
current backend/frontend seam; it does not add an endpoint, change research
behavior, or approve a milestone.

## Authority and routing

The active machine-readable records remain `.project/project-profile.yaml`,
`.project/framework-ref.yaml`, `.project/project-state.yaml`, and
`config/conditions.json`. The client must read capability from the server and
must not invent, substitute, or silently fall back between profiles,
conditions, providers, models, or retrieval backends.

- Inference is local-only through Ollama. `fake`/`FakeProvider` is a
  deterministic wiring/test double, never semantic or milestone evidence.
- M0 exposes A only; M1 exposes A/B/C; M2 exposes A/B/C/C-P/C-N/C-O. A is
  Vanilla RAG with P/N/O off.
- P is Retrieval-Guided Task Decomposition, N is conservative exact-duplicate
  Task Normalization, and O is Overlap-Aware Context Allocation. Their
  semantics and A/B/C comparability are unchanged by this product contract.

## Domain identities

```text
Conversation (owner-scoped grouping) -> Message turns -> RunRecord (immutable persisted execution)
Current user message + bounded authorized history -> existing pipeline request understanding
Source -> Chunk (canonical inspectable support unit)
TaskResult -> evidence_ids/citations -> Chunk
P-lite plan -> planning evidence (never answer evidence)
Local user -> hashed credential/session -> USER or ADMIN product boundary
```

The product must keep `Request`, `RunRecord`, `Source`, `Chunk`, task,
evidence, citation, and planning evidence distinct. A role label or task is not
proof that an agent was spawned. History can select a stored conversation or
run; reopening never replays, edits, or compares an execution.

## Backend/frontend endpoint contract

All paths are under `/api`. Success payloads are JSON unless noted. Optional
and additive fields may be absent; clients preserve unknown status/fields.

| Method and path | Request | Returned contract | Frontend responsibility |
| --- | --- | --- | --- |
| `GET /health` | — | `HealthResponse`: profile, allowed conditions, provider/config/snapshot and KB summary when available. | Gate capability and show readiness; health is not run evidence. |
| `GET /config` | — | Public runtime config, local model/provider, retrieval identity, allowed conditions, `config_hash`. | Display returned identity; never hard-code future availability. |
| `GET /local-model/health` | — | Local diagnostic (`ok`, safe `message`/`error`, `code`, `retryable`, model). | Keep diagnostic separate from answer/run status. |
| `GET /kb/status` | — | `KnowledgeBaseStatus`: `EMPTY`/`READY`/`FAILED`/`UNAVAILABLE` or additive status, counts, backend, snapshot. | Distinguish corpus readiness from run status; retry only the affected area. |
| `GET /sources` | — | `{snapshot_id, sources[]}` with source identity/count/type/index status. | List corpus sources; an error is not an empty corpus. |
| `GET /sources/{source_id}` | path ID | `SourceDetail` with canonical `chunks[]`. | Show provenance and readable source/chunk context. |
| `GET /chunks/{chunk_id}` | path ID | `SourceChunk` (`chunk_id`, source, text, index, optional score/provenance). | Link only returned valid locators; no fabricated claim offsets/highlights. |
| `POST /sources/text` | `{source_name, text}` | `SourceImportResult` with source, chunks, snapshot/index fields. | Import is additive; do not create a run. |
| `POST /sources/file` | multipart `file` | `SourceImportResult`; P0 file boundary is local UTF-8 text/code/Markdown, max 2 MB. | Show upload/index phases and scoped error/retry. |
| `POST /chat` | `{message, condition?, provider?}`; message must be non-blank. | One persisted `RunRecord`. | Preserve the submitted request; no duplicate pending submit or implicit fallback. |
| `GET /runs` | — | `RunListItem[]` (`run_id`, time, condition/query/status when present). | Flat recent-run navigation; loading/error is distinct from empty. |
| `GET /runs/{run_id}` | path ID | Exact persisted `RunRecord`. | Reopen read-only; 404 is an inspection error, not `NO_EVIDENCE`. |
| `POST /tasks/decompose` | `{request, provider?}`; request must be non-blank. | P-lite inspection response with bounded tasks, dependencies, warnings, and planning evidence. | Research/Demo only when active profile permits; no run creation or chat fallback. |
| `POST /auth/register` | local email/name/password | authenticated user/session and opaque access token at the explicit registration boundary. | Keep credentials local; never render password/token material. |
| `POST /auth/login` | local identifier/password | authenticated user/session and opaque access token at the explicit login boundary. | Persist same-origin session cookie; show scoped error on failure. |
| `POST /auth/logout` | session cookie/header optional | `{ok, authenticated:false}` and revoked local session. | Return to S00 without mutating runs or sources. |
| `GET /auth/session` | session cookie/header optional | authenticated user/session or `authenticated:false`. | Restore local session; expiry is distinct from runtime/offline. |
| `GET /settings` | optional local session | safe local runtime, corpus, and user settings summary. | Do not expose environment secrets or infer permissions. |
| `GET /admin/status` | ADMIN session required | bounded local runtime/auth status. | Hide from regular users; preserve 401/403 semantics. |
| `GET /admin/users` | ADMIN session required | safe public user list/count. | Never return password/token hashes. |
| `GET /history` | — | bounded persisted run list (alias of `/runs`). | Keep history read-only; lookup errors are not empty history. |
| `POST /conversations` | optional `{title}`; authenticated local user required. | Owner-scoped `Conversation` with stable ID and empty messages. | Start a clean thread boundary. |
| `GET /conversations` | authenticated local user required. | `{conversations[]}` owned by the caller. | List threads; 401/error is not an empty list. |
| `GET /conversations/{conversation_id}` | owned conversation ID. | Conversation with ordered `USER`/`ASSISTANT` messages and optional `run_id`. | Reopen a thread without replay. |
| `POST /conversations/{conversation_id}/messages` | `{message, condition?, provider?}`; owned conversation and non-blank current message. | `{conversation, user_message, assistant_message, run}`. | Show current turn and preserve run/citation inspection. |
| `GET /runs/{run_id}/trace` | path ID | persisted trace/effective config/metrics. | Technical disclosure only; no self-approval. |
| `GET /runs/{run_id}/evidence` | path ID | resolved canonical evidence items plus missing IDs. | Link only returned evidence; preserve missing state. |

The current frontend uses the routes above. Other backend routes are not P0
product promises unless added through a separately reviewed contract.

## RunRecord and terminal states

The returned run keeps these fields together (some are additive/optional in
older records):

```text
run_id, created_at, conversation_id?, condition, implementation_profile,
provider, model, query, status, answer,
source_snapshot_id, config_hash, effective_config,
tasks, task_results, events, metrics
```

`task_results[]` carries the task status/answer, `evidence_ids`, valid
`citations`, `invalid_citations`, missing information, and optional reason.
Canonical chunk IDs are the only linkable answer evidence. Planning IDs stay
in the planning boundary.

| Status | Meaning | Required UI treatment |
| --- | --- | --- |
| `COMPLETE` | Returned task results are complete with validated support. | Show answer and support; never label as semantic correctness or approval. |
| `PARTIAL` | Answer or information/citation validation is incomplete. | Keep answer; show missing information and valid/invalid split. |
| `NO_EVIDENCE` | No answer-domain support was validated. | Say so plainly; empty citation state; suggest refine/add source. |
| `FAILED` | Pipeline/API/runtime execution failed. | Show safe reason/recovery; never relabel as no evidence. |
| unknown | Additive/future status. | Preserve raw value and use neutral copy; do not coerce to success. |

Run events are the raw trace. The UI may summarize only stages actually
returned (for A typically `run_started`, retrieval, and `run_finished` or
`run_failed`). Metrics are runtime measurements: `0` is measured zero and
`null`/missing is unavailable, not a correctness or faithfulness score.

## Error and lifecycle contract

Non-2xx responses use the additive envelope:

```json
{"detail": "...", "code": "STABLE_ERROR_CODE", "message": "...", "retryable": false}
```

Clients prefer `message`, then `detail`, then legacy `error`, retain the HTTP
status, and scope recovery to the failed operation. A pending request is a UI
state, not a persisted run. History/source/chunk/plan lookups do not mutate a
run. Retrying a chat request creates a new explicit run; cancellation and
background retry are not contracted.

## Frontend invariants

1. Answer canvas is primary; history, corpus, evidence, runtime, and research
   panels are contextual and must remain reachable at supported widths.
2. Keep question, run identity, condition/profile, provider/model, snapshot,
   config hash, status, answer, citations, events, and metrics bound together.
3. Distinguish corpus `EMPTY/READY/FAILED/UNAVAILABLE`, request/API errors,
   and run terminal states. Do not turn a lookup error into `NO_EVIDENCE`.
4. Make only validated canonical citations actionable. Keep invalid locators,
   missing information, and no-evidence states visible and separate.
5. Preserve unknown fields/statuses, format unavailable metrics as `—`/`Not
   available`, and never manufacture claim highlights, agents, scores, or
   stages.
6. Normal ↔ Research/Demo changes presentation disclosure only. It must not
   change condition, provider, model, corpus, prompt budget, run, or milestone.
7. Local auth is a product boundary, not a research identity claim. The client
   never grants ADMIN; role checks are enforced by the server and reflected in
   the returned session.

## Conversation and context invariants

- A conversation and a run are different identities. Every conversation message
  has a role, timestamp, and optional associated `run_id`; the run remains the
  immutable research record.
- Conversation reads and writes are owner-scoped. A missing/unauthorized ID is
  a scoped `404`/`401`, never a fallback to another user's history.
- The context builder is one deterministic bounded component: it uses only the
  authorized conversation, excludes the current message, keeps a recent capped
  set of turns/chars, and may validly return empty context.
- The pipeline envelope distinguishes `current_request`, `conversation_history`,
  and retrieved KB evidence. Conversation history is never an evidence ID or
  citation target; citations resolve only to canonical source chunks.
- A topic switch remains a new current request. No embeddings, summaries,
  cross-conversation memory, or memory agent are introduced by P0.

## Anti-QA handoff boundary

Anti-QA review should exercise the endpoint/screen pairs in
`FEATURE_SCREEN_MAP.md`, inspect one valid citation and one missing/invalid
path, and confirm immutable history/recovery. It should record live/static
evidence separately and retain raw run/error data. Documentation, unit tests,
screenshots, static checks, and FakeProvider output cannot promote M0, M1, or
M2; the existing `.project/project-state.yaml` remains authoritative.
