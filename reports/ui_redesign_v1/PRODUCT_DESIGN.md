# Local Multi-Agent RAG — Product Design V1

**Status:** final product/UX direction for implementation review; documentation only
**Date:** 2026-09-07
**Reviewed revision:** `main@baadfaf`
**Scope:** information architecture, modes, interaction/state contracts, visual direction, responsive/accessibility constraints, and acceptance criteria.
**Not in scope:** frontend or backend code, research logic, datasets, benchmarks, provider/model changes, source deletion, run cancellation, or milestone approval.

## Decision summary

Local Multi-Agent RAG is an **evidence desk**: a calm local research instrument
for asking a question against an imported corpus, reading a bounded answer, and
moving from an answer claim to the source chunk that supports it.

V1 makes five product decisions:

1. **Normal mode is the first-run default.** The answer and source context are
   the focal task. Research/Demo mode is an explicit presentation mode for
   reviewers; it does not change the research condition, provider, prompt, or
   backend capabilities.
2. **The shell is answer-first.** Desktop has a left context rail, a central
   answer canvas, and an optional right evidence inspector. The inspector is a
   contextual drawer, not a peer application that competes with the answer.
3. **The evidence thread is the signature interaction.** A validated citation
   is an accessible link to a source/chunk context drawer. The drawer opens at
   the selected locator, preserves the answer position, and returns focus to
   the citation.
4. **Research detail is progressively disclosed.** Human explanations come
   before raw IDs, event stages, token estimates, snapshot IDs, and config
   hashes. Exact evidence remains available in Research/Demo mode and in a
   technical-details disclosure.
5. **Every state is explicit and honest.** Booting, offline/degraded, empty
   corpus, running, `COMPLETE`, `PARTIAL`, `NO_EVIDENCE`, `FAILED`, and unknown
   future statuses have distinct copy and recovery behavior. A wiring/test
   result is never presented as semantic evidence or milestone completion.

The first implementation review should evaluate this document against the
current frontend contract, not against a screenshot or a green visual state.

## Product intent and boundaries

### Primary humans

- **Normal researcher/student:** has a local corpus and a question; needs a
  readable answer, source context, and a clear explanation when evidence is
  incomplete or absent.
- **Research/Demo reviewer:** needs to inspect the same run's condition,
  implementation profile, provider/model, retrieval trail, planning result,
  configuration identity, metrics, and failure boundary without confusing
  wiring evidence with semantic or milestone evidence.

### Desired feel

Calm local evidence desk / laboratory instrument: quiet enough for reading,
provenance-visible, technically honest, and precise. It is not a generic chat
app, a colorful metrics dashboard, or an unfiltered terminal dump.

### Non-negotiable research and runtime boundaries

- Preserve P/N/O semantics and the A/B/C comparison design. This design adds no
  research module and does not reinterpret a condition.
- M0 remains A-only. An unavailable condition/profile is rejected; mode changes
  must never create a silent fallback.
- FakeProvider is a wiring/test double. Label it as **wiring/test only** and
  never use a successful Fake run, static UI, or screenshot to imply semantic
  quality or milestone completion.
- Keep source/chunk provenance, canonical citation IDs, valid versus invalid
  citation separation, explicit `PARTIAL`/`NO_EVIDENCE`/failure states,
  immutable effective configuration, trace, and resource-limit evidence.
- Do not promise source deletion, undo, run cancellation, retry policies, or
  metrics that are not in the current API contract.
- Keep provider bodies, credentials, stack traces, and unsafe diagnostic data
  out of Normal mode and out of any user-facing artifact.

## Domain exploration

### Domain vocabulary

The interface should use the product's evidence-world concepts instead of
generic dashboard labels:

- corpus / source — the local evidence collection;
- chunk / locator — the smallest inspectable support unit;
- provenance — the path from answer to source, chunk, snapshot, and validation;
- retrieval trail — candidates considered, selected evidence, dropped evidence,
  and reasons;
- bounded context window — the resource limit on what reaches generation;
- question / run — a request paired with an immutable execution record;
- task graph / decomposition — optional planning structure, separate from the
  answer's evidence;
- citation audit — valid, invalid, missing, or not-evaluated locator state;
- local runtime — provider/model and measured runtime identity on this machine;
- calibration / milestone boundary — research context, not an answer-quality
  score.

### Color world

The visual world is a warm paper-and-instrument workspace:

| Material or signal | Product meaning | Direction |
| --- | --- | --- |
| paper / ivory | reading canvas and empty states | dominant, low-contrast base |
| graphite / ink | answer copy and structural headings | highest text contrast |
| muted teal | provenance links, selected evidence, local signal | one interaction accent |
| slate mist | drawer, inactive structure, quiet grouping | secondary surfaces |
| amber | running, partial, weak, needs review | never a success color |
| rust red | failed run or invalid locator | paired with text and icon |
| soft moss | ready/complete confirmation | paired with text and icon |

Color communicates evidence and state; it does not decorate every card or make
conditions A/B/C look like competing brands.

### Product signature: the evidence thread

The evidence thread is the visual and interaction motif across the product:

`answer claim or citation → source/chunk context → retrieval/audit detail → return`

Every validated citation is an accessible entry into that thread. Source name
and readable excerpt lead. The locator, snapshot identity, validation reason,
selection/drop rationale, and raw trace are progressively disclosed. The user
can inspect support without losing the answer's position.

The current API returns canonical citation IDs per task result, but not
character offsets or a claim-to-citation map. Therefore V1 must not fabricate
highlighted claim spans. Where an exact inline position is unavailable, render
a clearly labeled, focusable **Validated evidence** strip directly under the
answer/task result; the interaction and drawer remain the same. If a future
response supplies claim anchors, the strip can become true inline markers
without changing the drawer contract.

### Defaults explicitly rejected

| Obvious default | V1 decision |
| --- | --- |
| Generic three-column SaaS dashboard | Answer canvas first; rails support it and the inspector is optional. |
| Terminal/dark-mode overload | Warm reading surfaces; monospace only for IDs, hashes, and measured values. |
| Every metric as a colorful card | Small measured summary with units; details are progressive. |
| Raw trace as the product | Human stage narrative first; raw events/IDs on demand. |
| Citation as a passive badge | Focusable evidence link with source context and return focus. |
| Hide side panels on mobile | Convert history, corpus, and evidence into reachable drawers/sheets. |
| Green screen equals research success | Status and evidence boundary remain explicit; no milestone implication. |

## Information architecture

### Primary shell

```text
AppShell
├── Skip link → #answer-canvas
├── WorkspaceHeader
│   ├── workspace / corpus identity
│   ├── Normal ↔ Research/Demo mode switch
│   ├── compact local-runtime status (always visible)
│   └── Research/Demo: condition / profile / provider / model context
├── ContextRail (desktop) or ContextDrawer (tablet/mobile)
│   ├── New question / New run
│   ├── Recent runs
│   └── Corpus / source library summary
├── AnswerCanvas (always primary)
│   ├── page title and corpus readiness
│   ├── QuestionComposer
│   ├── current question
│   ├── RunStateBanner (one authoritative state)
│   ├── AnswerBlock
│   │   ├── answer copy
│   │   ├── evidence summary / citation links
│   │   └── missing-information or evidence-boundary note
│   └── Normal: concise runtime summary; Research/Demo: research boundary
└── EvidenceInspector (optional right drawer / mobile sheet)
    ├── source context (first)
    ├── retrieval trail and citation audit
    ├── source library / chunk detail
    ├── runtime metrics and run identity
    └── planning-only task view when the active profile permits it
```

### Desktop composition

- **Context rail:** approximately 232–248px when open. It communicates
  navigation and corpus context, not raw runtime metadata.
- **Answer canvas:** flexible central region. Keep the answer reading measure
  near 720–800px and let surrounding space breathe. The answer is the single
  focal element of the view.
- **Evidence inspector:** approximately 360–420px when open. It is closed by
  default in Normal mode and opened by an explicit evidence/inspect action. It
  may overlay the right side when space is constrained; it must not squeeze the
  answer into an unreadable measure.
- **Depth:** quiet low-opacity dividers and tonal surface changes define the
  shell. Use one subtle shadow only for a drawer/popover. Do not create three
  unrelated card elevations.

### Workspace header

The header is a stable orientation surface, not an experiment dashboard.

Normal mode shows:

- workspace/corpus name;
- `Normal` mode selected and a clear control to switch to `Research/Demo`;
- compact runtime state such as `Local runtime ready`, `Connecting`, or
  `Local runtime unavailable`;
- an unobtrusive local-only explanation.

Research/Demo mode additionally shows condition, implementation profile,
provider/model, and the active run identity when known. These fields are
labeled in plain language and raw values can be copied from the inspector.

The condition is not an editable mode control. In M0 it displays A / the
locked vanilla path; unsupported conditions are not shown as selectable
options. Provider selection remains available through an explicit **Run
options** disclosure. If FakeProvider is selected, its `wiring/test only`
qualification is visible before and after submission even in Normal mode.

### Context rail / drawer

The rail has three jobs, in this order:

1. **Start a question:** `New question` is the primary action and returns the
   answer canvas to a ready state without deleting history.
2. **Reopen a run:** recent runs are titled by a readable query excerpt, time,
   and human status. Condition letters and run IDs are secondary details.
3. **Find corpus material:** show source names and chunk counts; IDs appear in
   source details, not as the first label.

The rail footer may show the corpus snapshot/source count and local-only status.
An empty history list says no runs have been completed yet; it must not appear
while booting. An empty corpus state points to `Add a source` rather than a
generic blank panel.

Selecting a history item loads that immutable run and resets the inspector to
its evidence context. The active item has a non-color selection treatment.
While a run is pending and cancellation is unavailable, history/new-run
controls either remain visibly locked with an explanation or open read-only
context without replacing the pending run. They must never mix the old run's
metadata with the new question.

### Answer canvas

The answer canvas is the primary route for both modes. Its hierarchy is:

1. corpus readiness and page title;
2. labeled multiline question composer with source import;
3. current question, retained from submission through resolution;
4. one `RunStateBanner`;
5. answer copy, evidence links, and missing-information explanation;
6. a compact runtime/evidence summary;
7. optional actions to inspect context or switch to Research/Demo.

Normal copy should say `Ask your local corpus`, `Ready to ask`, `Answer ready`,
or `No validated evidence found`. It should not lead with `M0 research
console`, `P-lite`, `vanilla retrieval`, or raw IDs. Research/Demo may show
exact terms, but each technical term gets a short human explanation.

### Optional evidence inspector

The inspector is a right-side drawer on desktop and a full-height sheet or
route-like drawer on narrow screens. It opens from a citation, `Inspect
evidence`, `Sources`, or the Research/Demo controls. Source context is the
first view; trace, metrics, and plan are deliberate secondary views.

Recommended sections:

1. **Context:** source name, chunk number, excerpt, validation state, and a
   `Back to answer` action.
2. **Evidence trail:** human stage narrative, selected/dropped evidence, drop
   reasons, task association, and citation audit.
3. **Sources:** friendly source list, chunk count, source detail, and chunk
   previews.
4. **Run details / metrics:** status, measured values and units, run ID,
   snapshot ID, config hash, provider/model, and effective configuration in
   Research/Demo mode.
5. **Plan:** P-lite planning evidence and task/dependency inspection only when
   the active profile allows it. It is explicitly marked `Planning only` and
   never implies that a task is a spawned agent or an answer citation.

If tabs are used, implement a complete accessible tab pattern. Otherwise use
native buttons with disclosure panels and avoid a partial `role="tab"`
implementation. The drawer title identifies the selected run/source and its
close control is always reachable.

## Normal mode versus Research/Demo mode

Mode is a presentation boundary. It does not switch conditions, providers,
models, prompt budgets, corpora, or research milestones. Switching modes keeps
the active run, current question, and drawer selection intact.

| Concern | Normal mode (default) | Research/Demo mode |
| --- | --- | --- |
| Primary goal | Ask, read, verify | Inspect, compare, and explain limits |
| Header | Corpus identity, mode, local runtime state | Same plus condition/profile/provider/model and run identity |
| Question | Simple labeled composer and source import | Same composer plus explicit run options and boundary labels |
| Answer | Large readable answer; evidence count and source names | Same answer plus evidence/quality boundary and per-task context |
| Citation | Validated source links/strip; readable excerpt first | Raw canonical locator, task association, validation, and technical details |
| Loading | One concise progress sentence; retained question | Stage timeline only for stages actually returned; no fabricated percentage |
| Metrics | Small latency/evidence summary; unavailable values omitted or explained | Full available runtime metrics with units; `—`/`Not available` is explicit |
| Plan/tasks | Hidden until requested | Available only when profile permits; labeled P-lite/planning only |
| Provider | Run option; Fake is visibly `wiring/test only` | Provider/model and local-only identity are explicit |
| Error | Safe reason and next action | Same plus error code/status/retryability in technical details |
| Mobile | Context and evidence remain reachable via drawers/sheets | Full research inspector remains reachable; no trace loss |

Normal mode is intentionally not “less honest.” It prioritizes the explanation
most people need first. The technical layer remains available when it affects
trust or when the user asks to inspect it.

## Screen and component hierarchy

### Reusable component contract

| Component | Responsibility | Must not do |
| --- | --- | --- |
| `AppShell` | Own responsive geometry, mode boundary, landmarks, and drawer state | Delete capabilities at a breakpoint |
| `WorkspaceHeader` | Orient the user and expose mode/runtime status | Pretend a mode switch changes research configuration |
| `ContextRail` / `ContextDrawer` | New question, recent runs, source library entry | Lead with raw IDs or hide history on mobile |
| `QuestionComposer` | Labeled multiline question, import, submit state, preserved draft | Clear the question before the request resolves |
| `RunStateBanner` | One authoritative state, explanation, next action | Duplicate competing running/error callouts |
| `AnswerBlock` | Focal answer, evidence links, missing-information note | Claim quality beyond returned evidence |
| `CitationLink` | Keyboard-focusable bridge to a canonical chunk | Link an invalid locator or planning ID as validated evidence |
| `EvidenceDrawer` | Context-first source/chunk inspection and focus return | Replace the answer or fabricate a claim highlight |
| `SourceList` / `SourceDetail` | Friendly corpus browsing and chunk inspection | Expose source IDs as the only label |
| `TraceTimeline` | Human narrative of returned stages and evidence accounting | Invent stages, agents, retries, or scores |
| `TaskGraph` / `TaskList` | Planning-only tasks and dependencies | Call a role profile a spawned agent |
| `MetricsSummary` | Measured runtime values with units and availability | Render unavailable values as zero or quality scores |
| `StatusBadge` / `StatusMessage` | Text + shape/icon + color state communication | Use color alone or collapse unknown states |
| `LoadingState`, `EmptyState`, `ErrorState` | Consistent title, explanation, and next action | Present loading as successful emptiness |

### Component hierarchy inside a run

```text
RunView
├── QuestionCard
├── RunStateBanner
│   ├── status label
│   ├── short explanation
│   └── next action, when applicable
├── AnswerBlock
│   ├── answer copy
│   ├── evidence summary
│   ├── ValidatedEvidenceLinks (per task when available)
│   ├── MissingInformationNote (PARTIAL/NO_EVIDENCE)
│   └── EvidenceBoundaryNote (Research/Demo)
└── RuntimeSummary
    ├── Normal: concise measured summary
    └── Research/Demo: inspect drawer trigger
```

One view has one focal action. On a ready screen it is asking a question; on a
complete screen it is reading/verifying the answer; on a partial/no-evidence
screen it is deciding whether to refine the question or add corpus material.

## Interaction rules

### Starting and submitting a question

1. The question control has a visible label, multiline behavior, and a submit
   button with a disabled state for blank input.
2. Enter submits only when not composing a new line; Shift+Enter creates a new
   line. The control may auto-grow to a bounded height, then scroll internally.
3. Preserve the trimmed submitted question in the conversation and pending
   state until the request resolves or fails. Do not clear it optimistically.
4. While running, disable conflicting submit/context-switch actions. Do not
   show a cancel control unless a separate backend contract adds cancellation.
5. A retry repeats the same visible question and explicitly chosen
   condition/provider. It never changes condition/provider to force success.
6. Starting `New question` clears only the editable draft/active answer view;
   it does not delete history, corpus sources, or the prior immutable run.

### Importing a source

- `Add a source` is primary when the corpus is empty and remains available from
  the composer/rail.
- State the supported UTF-8 text/code formats and the current 2 MB file cap at
  the import affordance. Use a real labeled file input, not only an icon title.
- During import, keep the current answer visible and show progress at the
  import action. Disable duplicate import activation, not the whole product.
- Success identifies the source name, chunks added/total, and new snapshot when
  available. Offer `View source` and `Ask a question` as durable actions; do
  not rely on a short-lived toast.
- Failure stays next to the import action, gives a safe reason and retry/fix,
  and does not change the current corpus summary as if the import succeeded.
- V1 does not promise delete, undo, replacement, or source reordering because
  those operations are not in the current contract.

### Run history and source browsing

- Show a human-readable query excerpt, status, and relative/short date first.
  Expose run ID, condition, and snapshot in Research/Demo details.
- A history item loads its persisted `RunRecord`; it does not recompute or
  mutate it.
- Loading a source or chunk shows an inline skeleton/state in that item. Keep
  the prior selection until the new selection succeeds when possible.
- A source/chunk 404 or fetch error is an inspection error, not a
  `NO_EVIDENCE` run.
- Long source names and IDs wrap or expand; never make the only copy an
  inaccessible ellipsis.

### Evidence thread and citation drawer

1. A validated canonical citation is a focusable link/button with a readable
   label such as `View evidence from api.md, chunk 2`. The raw locator remains
   available in details.
2. Activating it opens the inspector at the matching chunk and adds a visible
   heading such as `Evidence for this answer`. Keep the answer scroll position.
3. Drawer order is: source name → chunk number/locator → validation state →
   readable excerpt → related task/missing-information context → technical
   details. Do not lead with a hash.
4. The drawer exposes `Back to answer` and close. On close, restore focus to the
   citation that opened it; if that trigger disappeared, focus the answer
   heading and announce the fallback.
5. Use `aria-expanded`, `aria-controls`, a labeled drawer heading, and a
   dialog/sheet focus contract appropriate to the surface. Escape closes an
   overlay and returns focus.
6. Invalid locators remain visible as a separate `Needs review`/`Not validated`
   state with the returned reason where available. They are not clickable
   source links, and the UI must not call `GET /api/chunks/{id}` as though they
   were valid.
7. If a valid locator cannot be loaded, show `Evidence could not be loaded`
   with retry and the raw locator in Research/Demo details. Do not relabel it
   as `NO_EVIDENCE`.
8. When the current response has no claim offsets, do not highlight invented
   text. Use a validated-evidence strip under the answer and say `These chunks
   were returned as support for this task`.
9. Deduplicate repeated canonical IDs in the Normal visual list while keeping
   the research trace/task association available. Never transform a planning
   evidence ID into an answer citation.

### Research/Demo inspection

- The mode switch is a presentation toggle only and can be changed without a
  new run.
- Show the exact returned status and unknown future statuses. Never coerce an
  unknown value to `COMPLETE`.
- Evidence details may show candidate/selected/dropped IDs, reasons, estimated
  tokens, stage, task ID, timestamps, citation counts, snapshot ID, config hash,
  and effective config when returned.
- Trace summaries must report only stages present in `events`. No UI label may
  imply an agent, retry, escalation, or task execution that the run record does
  not contain.
- The P-lite plan action appears only when the active profile permits it. The
  plan view states that planning evidence guides decomposition and is distinct
  from answer-domain evidence. No task count is presented as an agent count.
- `NOT_EVALUATED` is a qualifier for human quality review, not a failure state
  and not a green success signal.

## Loading and progress model

### Shell boot

Use a page-level skeleton for header, context rail, answer title, and composer
while health/sources/history load. Show a concise `Connecting to local runtime…`
status. Do not display `Corpus is empty`, `No run selected`, or `No completed
runs` until each relevant request has resolved.

If one boot request fails and others succeed, show `Some workspace data is
unavailable` with the affected area and retry. Keep successful data visible.
`OFFLINE`/`DEGRADED` is a shell state and must not be rendered as an ordinary
empty corpus.

### Source import

The import button shows a local pending indicator and remains associated with
the import control. On completion, replace it with a durable source result
card. Do not block answer reading while a source list refreshes.

### Run progress

Use one authoritative `RunStateBanner` plus a compact live status sentence:

- default: `Retrieving evidence…`;
- when the returned/request boundary explicitly exposes it: `Validating
  citations…` or another bounded stage label;
- unknown/intermediate: `Working locally…`.

Do not show fabricated percentages, countdowns, token estimates, agent names,
or stage completion. Preserve the user question and do not display the
previous run's run ID/provider/status beside the pending request. The prior
run remains in history as an immutable item.

### Inspector progress

Loading a source, chunk, or plan uses an inline skeleton/`Loading…` state at
the selected item. The rest of the inspector remains understandable and can
retain prior content. A failed detail request has a local retry action and a
safe error message.

## State and copy contract

The shell state and the run status are related but not identical. `BOOTING`,
`OFFLINE`, `DEGRADED`, `READY_EMPTY`, and `READY` describe the workspace;
`RUNNING`, `COMPLETE`, `PARTIAL`, `NO_EVIDENCE`, `FAILED`, and unknown values
describe a run. `INSPECTING_CONTEXT` is a drawer substate, not a new run
status.

| State | Primary copy | Required content | Primary action | Never do |
| --- | --- | --- | --- | --- |
| `BOOTING` | `Connecting to your local workspace…` | Shell skeleton; no false empty text | Wait; retry if a request fails | Say the corpus/history is empty |
| `OFFLINE` | `Local runtime unavailable` | Safe category, last-known data if available | `Retry connection` | Hide reachable cached context or invent a run |
| `DEGRADED` | `Some workspace data is unavailable` | Area-specific partial-boot notice | Retry affected area | Treat partial boot as success |
| `READY_EMPTY` | `Add a source to begin` | Accepted formats/cap, local-only explanation | `Add a source` | Present a blank dashboard |
| `READY` | `Ready to ask` | Source count/chunk summary, labeled composer | Ask a question | Lead with condition/provider internals |
| `RUNNING` | `Retrieving evidence…` | Preserved question, one status, bounded stage if known | Wait; no fake cancel | Mix stale run metadata into pending card |
| `COMPLETE` | `Answer ready` | Answer, valid support links/count, measured summary | Read / inspect evidence | Claim semantic quality or milestone completion |
| `PARTIAL` | `Answer needs review` | Answer remains visible; missing info; valid/invalid split | Inspect gap, refine, or add source | Paint as complete or discard useful answer |
| `NO_EVIDENCE` | `No validated evidence found` | Explicit answer/status; empty citations; missing reason | Refine question / add source | Invent a source link or equate to 404 |
| `FAILED` | `Run failed` | Safe reason/category, retained question, retry/repair if safe | Retry same request or repair | Change provider/condition silently |
| unknown status | `Status received: <value>` | Preserve raw status in Research/Demo, neutral tone | Inspect/retry only if safe | Coerce to `COMPLETE` |
| `INSPECTING_CONTEXT` | `Evidence context` | Drawer focus/selection state | Return to answer / close | Replace the run's terminal status |

### Terminal status details

- **`COMPLETE`:** every returned task result is complete and has validated
  support. Show the answer and valid citation links. A run being complete is
  an execution result, not a human correctness or faithfulness score.
- **`PARTIAL`:** keep the bounded answer visible. Aggregate
  `missing_information` by task where possible; keep valid and invalid
  locators visually separate. Suggested copy: `Some support is incomplete.
  Review the missing items before relying on this answer.`
- **`NO_EVIDENCE`:** show the explicit no-evidence answer, an empty citation
  state, and a next step. `citation_locator_validity: null` is unavailable, not
  zero.
- **`FAILED`:** use `message`, then `detail`, then the legacy error field from
  the safe API envelope. Show `code`/HTTP status/retryability in Research/Demo
  details when present. Never expose raw provider bodies or credentials.

### Metrics and quality boundary

Normal mode may show a compact `Runtime measured` summary such as latency and
validated citation count. Research/Demo may show all available fields from
`RunMetrics`, each with a unit. Missing values render as `—` or `Not
available`, never as zero. Do not invent cost, retry, escalation, or quality
fields.

Human `manual_correctness` and `manual_faithfulness` remain blank/
`UNSCORED`; the UI must not synthesize them from citation counts, latency, or
FakeProvider output. Use `Quality not evaluated in this view` as a research
qualifier, with an explanatory disclosure rather than a warning color.

## Citation, provenance, and plan rules

The frontend contract has no top-level `citations` or `missing_information`
field. The design therefore requires the presentation layer to aggregate
`task_results[].citations`, `invalid_citations`, `evidence_ids`, and
`missing_information` while retaining task association in Research/Demo.

- Valid citations/evidence are canonical chunk IDs returned by the backend.
  Model-facing `E1`, `E2`, and similar labels are not stable UI locators.
- Invalid locators are evidence of a validation problem, not a source. Show the
  reason when returned and never render them as validated links.
- Planning evidence IDs and context belong only to the plan view. They are not
  answer-domain citations and cannot open the answer evidence drawer unless a
  separate canonical chunk ID is returned.
- The evidence trace may summarize selected/dropped candidates and bounded
  context, but must preserve unknown fields/stages in technical details rather
  than rewriting them.
- `source_snapshot_id`, `config_hash`, provider/model, condition, profile, and
  effective configuration stay bound to the run in Research/Demo details.
- A 404 source/chunk/run lookup is an API/inspection error; it is not a
  `NO_EVIDENCE` run.

## Visual and design-system direction

### Semantic token names

Token names should identify the evidence desk, not a generic gray dashboard:

```text
--paper            reading canvas / page background
--surface-1        answer cards and composer
--surface-2        inspector / drawer
--surface-3        popover / selected context
--ink              primary answer text
--ink-secondary    supporting copy
--ink-muted        metadata / disabled copy
--line             quiet structural divider
--signal           provenance interaction teal
--signal-strong    focused/active provenance
--caution          running / partial / weak
--danger           failed / invalid locator
--success          ready / complete
--focus            keyboard focus ring
```

Every color maps to these primitives. Status color is paired with a readable
label and icon/shape. Keep semantic colors slightly desaturated on dark or
high-contrast variants; a dark theme is a future system decision, not a reason
to add arbitrary colors now.

### Typography and density

- Use an approved humanist sans or system equivalent for UI and answer copy;
  reserve a mono face for IDs, hashes, and measured values.
- Start at 15–16px body text with a roughly 1.25–1.333 type ratio: readable
  answer body, section title, page title. Use weight and color before tiny size
  changes.
- Reserve tracked uppercase eyebrows for genuine section context. Do not make
  every label a 9px experiment tag.
- Use a 4px spacing base and common values 4/8/12/16/24/32/40. Normal answer
  rhythm is 16px; evidence/trace can be tighter at 12px with 16–24px group
  separation.
- Minimum interactive hit area is 40px, with 44px as the touch target. Use
  tabular numerals for metrics and timers.
- Use quiet borders/tonal shifts for structure and one subtle shadow token for
  drawers/popovers. Avoid gradients and heavy card shadows.

### Motion

Motion is functional and short: drawer/popover entry under 300ms, press
feedback around 100–160ms, opacity/transform only, custom ease-out. Running
feedback may animate a small indicator but never block reading. Honor
`prefers-reduced-motion` by removing movement and retaining only necessary
opacity/color changes.

## Responsive behavior

The product must preserve capability, not merely preserve the central answer.

| Width class | Layout | Required behavior |
| --- | --- | --- |
| Large desktop (about 1440px) | Open context rail + answer canvas + optional inspector drawer | Answer measure stays near 760px; inspector can overlay/open at 360–420px. |
| Desktop/tablet (about 1024px) | Context rail may collapse; inspector overlays | Keep runtime/mode visible; do not shrink answer below readable measure. |
| Tablet (about 768px) | Context drawer + answer canvas; inspector as sheet | History, corpus, and evidence are reachable through explicit controls. |
| Mobile (about 390px) | Answer canvas plus full-width context/evidence sheets | No `display:none` content loss; safe-area padding and contained overscroll. |

Responsive rules:

- Keep runtime status and current mode visible at every width; use compact copy
  rather than hiding them.
- The context rail and evidence inspector become labeled drawers/sheets with a
  visible close/back path.
- A mobile evidence sheet may take the full viewport, but the answer remains
  the origin context and the user can return to the same citation.
- Keep the composer above the safe-area inset and avoid obscuring its submit
  action with the keyboard.
- Long IDs/source names wrap, expand, or copy; they do not cause horizontal
  page scroll.
- Keep scrolling contained within source/trace drawers when they are open.

## Accessibility and inclusive interaction

- Add a skip link to a stable `main#answer-canvas` target.
- Use semantic landmarks: header, navigation/context rail, main answer canvas,
  and complementary evidence inspector.
- Prefer native buttons, links, labels, `details`, and dialogs. If tabs are
  used, implement `aria-controls`, `tabpanel`, focus/arrow-key behavior, and
  selected state completely; otherwise use disclosure buttons.
- Every citation, drawer close/back action, mode toggle, source action, and
  provider control is keyboard reachable with a visible `:focus-visible` ring.
- Citation activation announces the drawer title and selected source. Closing
  restores focus to the originating citation; Escape closes overlays.
- Use `aria-live="polite"` only for a concise run/import/result sentence.
  Do not place the entire conversation or multiple nested status regions in a
  live region.
- Pair color with text and a shape/icon for complete, partial, no-evidence,
  failed, running, invalid, and offline states. Maintain text contrast and do
  not rely on the teal/amber/rust distinction alone.
- File input and question input have explicit accessible names and help text.
  Errors are associated with the affected control and include a next action.
- Respect reduced motion, zoom/reflow, touch targets, text wrapping, and
  screen-reader reading order. Preserve answer content when panels collapse.

## Acceptance criteria

The redesign is ready for implementation review only when all criteria below
are mapped to a testable screen/state. These are product criteria, not evidence
of implementation or research completion.

| ID | Acceptance criterion | Verification |
| --- | --- | --- |
| IA-01 | Desktop shell has a left context rail, answer-first main canvas, and optional right inspector; the answer remains the focal surface. | Inspect at 1440px and confirm the answer leads visual hierarchy; close inspector without losing any answer content. |
| IA-02 | Context rail shows `New question`, readable recent runs, and corpus/source summary; raw IDs are secondary. | Load empty and populated history/corpus states; verify labels, active selection, and source counts. |
| IA-03 | Inspector opens contextually from a citation/source action and does not compete with the answer by default. | Open/close from answer and verify same scroll position and run identity. |
| MODE-01 | Normal mode is first-run default and hides technical metadata from the primary reading order. | Fresh session screenshot/manual review shows readable answer-first copy, not M0/provider/trace tags. |
| MODE-02 | Research/Demo reveals exact condition/profile/provider/model, trace, metrics, identities, and plan only when supported. | Toggle mode without a new request; compare the same run in both modes. |
| MODE-03 | Mode switching never changes condition, provider, model, prompt, corpus, or milestone state. | Inspect request payload/run identity before and after a mode toggle. |
| MODE-04 | FakeProvider is visibly `wiring/test only` in both modes and never reads as semantic proof. | Select Fake; verify qualification appears before submission and on the result. |
| STATE-01 | Booting has a skeleton/connecting state and never presents loading as an empty corpus/history. | Throttle or stub health/source/history responses; verify no false empty copy. |
| STATE-02 | Offline/degraded is distinct from empty and offers a safe retry while preserving available context. | Fail one or more bootstrap/detail requests; verify affected-area recovery. |
| STATE-03 | Running preserves the submitted question, has one authoritative progress message, and prevents stale run metadata/context mixing. | Submit while a prior run is selected; inspect pending view and controls. |
| STATE-04 | `COMPLETE`, `PARTIAL`, `NO_EVIDENCE`, and `FAILED` each have the required copy, evidence behavior, and next action. | Exercise or load one bounded artifact per terminal status; verify the state matrix. |
| STATE-05 | Unknown future status strings remain visible as neutral/unknown; they are not coerced to `COMPLETE`. | Render an unknown status fixture and inspect Normal/Research output. |
| STATE-06 | HTTP/API errors and source/chunk 404s are not represented as `NO_EVIDENCE` runs. | Submit blank/malformed/missing-resource cases and inspect status/run creation. |
| EVID-01 | Valid canonical citations are focusable evidence links; invalid locators are visibly separate and non-linking. | Fixture duplicate valid and invalid locators; verify link behavior and labels. |
| EVID-02 | Citation activation opens source name, chunk locator, validation state, readable excerpt, and safe return path. | Activate a valid citation; verify drawer ordering, close/return focus, and scroll retention. |
| EVID-03 | V1 does not invent claim highlights or source links when the contract has no offsets/mapping. | Review a response with only task-level canonical IDs; verify strip/fallback language. |
| EVID-04 | Planning evidence is separate from answer evidence and cannot be mistaken for a citation. | Open a P-lite plan; verify `Planning only`, IDs, warnings, and no answer-link treatment. |
| EVID-05 | Missing evidence is explicit: `PARTIAL` preserves useful answer text, `NO_EVIDENCE` has empty citations and a missing-information reason. | Inspect task-result fixtures and the aggregate run notice. |
| TRACE-01 | Research/Demo trace summarizes only returned stages, selected/dropped IDs, reasons, and counts. | Compare trace to raw events; verify no invented stage/agent/retry claims. |
| TRACE-02 | Metrics show units and `—`/`Not available` for absent values; no human quality score is inferred. | Fixture null/missing/zero metrics and inspect Normal/Research displays. |
| LOAD-01 | Import, chunk/source, and plan loading states are local and retryable without blanking unrelated content. | Trigger each request under delay/failure; inspect focus and visible context. |
| LOAD-02 | No fake cancellation, deletion, undo, cost, retry, or escalation affordance appears without a separate contract. | Review all actions in Normal and Research/Demo states. |
| RESP-01 | At 1024px, 768px, and 390px, history, corpus, evidence, mode, and runtime status remain reachable. | Manual responsive pass at 1440/1024/768/390; no core content is removed with `display:none`. |
| RESP-02 | Mobile sheets preserve safe-area padding, contained scroll, close/back path, and answer-origin return. | Test touch/keyboard sheet open-close and long source/chunk content. |
| A11Y-01 | Landmarks, skip link, labels, focus rings, target sizes, and status semantics are present. | Keyboard-only and screen-reader smoke pass; verify 40px minimum/44px touch targets. |
| A11Y-02 | Live regions announce concise asynchronous changes only; the conversation is not globally live. | Inspect accessibility tree during boot, run, import, and drawer transitions. |
| A11Y-03 | Reduced motion removes nonessential movement while preserving state visibility. | Enable `prefers-reduced-motion` and repeat drawer/run transitions. |
| VIS-01 | Visual tokens are semantic, warm-paper/ink/teal, one accent family, quiet depth, and deliberate type/density. | Squint/token review of implemented specimen; reject raw scattered colors/radii. |
| VIS-02 | The evidence thread is visible in at least five surfaces: answer links, evidence drawer, source detail, trace citation audit, and return-to-answer control. | Signature test against the component map. |
| BOUND-01 | UI remains local-only and uses documented backend routes; no provider credentials or direct hosted-provider calls enter the frontend. | Boundary scan and contract review. |
| BOUND-02 | The UI never presents a screenshot, Fake/static result, or completed run as M0/M1/M2 approval or semantic correctness. | Research/governance review of copy, status, and demo states. |

### Visual QA matrix for implementation

Before implementation is called visually ready, review at 1440px, 1024px,
768px, and 390px for:

- booting, offline/degraded, empty corpus, ready, running, complete, partial,
  no evidence, failed, and unknown status;
- long questions, long source names, long IDs, no metrics, duplicate citations,
  invalid citations, missing chunk, and missing plan;
- Normal and Research/Demo mode;
- keyboard-only navigation, focus restoration, reduced motion, zoom/reflow, and
  touch sheet interactions.

## Evidence boundary and handoff

**Inputs reviewed:**

- `reports/ui_ready/FRONTEND_CONTRACT.md`;
- `reports/ui_ready/CURRENT_UI_PROBLEMS.md`;
- `reports/ui_ready/REDESIGN_PREPARATION.md`;
- `reports/ui_ready/MANUAL_TEST_PACK.md`;
- current `frontend/src` components, API adapter, types, styles, entry HTML,
  README, and frontend tests;
- repository `AGENTS.md` and the local research governance rules.

**Output:** this product design document only.

**Files changed:** `reports/ui_redesign_v1/PRODUCT_DESIGN.md` only. Existing
frontend, backend, research, gold, benchmark, and runtime artifacts are
untouched.

**Tests/runtime:** no frontend build/test, backend run, Ollama call, benchmark,
pilot, or browser session was executed. This is an evidence-backed design
contract, not live visual QA or milestone evidence.

**Commit/push:** none.

**Next approval boundary:** a human should approve the default Normal mode,
mobile support expectation, and evidence-drawer contract before implementation.
After that review, implementation can be split into state contract, answer-
first shell, evidence thread, mode disclosure, trace/metrics, and responsive
accessibility QA slices without changing research scope.

The interface-design skill's patterns are intentionally captured here rather
than written to `.interface-design/system.md`; promote them to a shared system
file only after this direction is approved.
