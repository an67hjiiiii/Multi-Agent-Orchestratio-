# Sprint 2 QA, evaluation, and documentation handoff

## Scope and evidence boundary

This handoff covers only the MAI and CHUNG Sprint 2 quality/evaluation lane:

- `S2-MAI-01` through `S2-MAI-07`: integrity, provenance, retrieval
  relevance, citation validity, regression, calibration, and isolation QA.
- `S2-CHUNG-01` through `S2-CHUNG-04`: the evidence-relevance rubric,
  in/out-of-scope cases, fixed calibration scenarios, and QA-reviewed
  relevance/gap conclusions.

The work starts from base `0cbc9d05730caa1334cce26d147136564d4f0454` in the
assigned `cap1-s2-qa-docs` worktree. It changes tests and this report only. It
does not change product source, P/N/O, conditions, runtime, datasets, or gold
data. No Ollama run, experiment, or semantic self-approval is included.

The status vocabulary below is deliberate:

- `ADDED_FOCUSED_TEST`: a missing contract check was added in
  `tests/test_sprint2_quality.py`.
- `DOC_ONLY`: the task produces a reviewable rubric or conclusion, not
  executable product behavior.
- `VERIFIED_NO_CODE_CHANGE`: the existing approved baseline already exercises
  the seam; no empty task commit is manufactured.
- `PENDING_HUMAN_REVIEW`: static/automated evidence is not semantic approval.

## Fixed inputs inspected

| Artifact | Use in this handoff |
| --- | --- |
| `datasets/calibration/m0_cases.json` | Frozen 12-case calibration shape: nine evidence-present cases and three evidence-missing cases. |
| `reports/calibration/m0_calibration_fake_20260905T105713Z.json` | Existing FakeProvider wiring report; checked for case alignment, locator/source behavior, and explicit `UNSCORED` manual fields. |
| `reports/calibration/m0_calibration_fake_20260905T105713Z.csv` | Existing tabular companion; retained unchanged. |
| `datasets/domain/demo_security.md`, `demo_database.md`, `demo_api.md` | Fixed corpus content used for relevance examples and gap boundaries. |
| `reports/sprint1/S1_MAI_09_QUALITY_REPORT.md` | Prior approved reporting pattern and evidence boundary. |
| `tests/test_source_store.py`, `tests/test_pipeline.py`, `tests/test_source_owner_scope.py` | Existing source/chunk, run-state, and owner-isolation coverage. |

The required governance, member mapping, and student-code-standard documents
are available in the approved repository `main` snapshot but are not present
at this older assigned base. They were read from that snapshot and were not
copied into this worktree.

## Ownership mapping and result

| ID | Owner | Result and evidence |
| --- | --- | --- |
| `S2-MAI-01` | MAI | `ADDED_FOCUSED_TEST`: stable normalized chunk IDs, source scope, and index provenance in `tests/test_sprint2_quality.py`. |
| `S2-MAI-02` | MAI | `ADDED_FOCUSED_TEST`: A-run source snapshot, selected chunk IDs, evidence IDs, citations, effective config, and persisted trace remain linkable to `SourceStore`. |
| `S2-MAI-03` | MAI | `ADDED_FOCUSED_TEST`: matching fixed-corpus retrieval ranks the relevant source; a deployment-region query yields no hit at the configured threshold. |
| `S2-MAI-04` | MAI | `ADDED_FOCUSED_TEST`: invalid and duplicate citation locators are removed, status downgrades to `PARTIAL`, and only supplied IDs remain in the answer. |
| `S2-MAI-05` | MAI | `VERIFIED_NO_CODE_CHANGE`: existing `tests/test_pipeline.py` covers M0 A success, explicit `NO_EVIDENCE`, terminal provider failure, lifecycle trace, and rejection of B under `m0`. |
| `S2-MAI-06` | MAI | `ADDED_FOCUSED_TEST`: fixed case/report IDs, expected evidence modes, source labels, automated booleans, and `UNSCORED` manual fields agree. |
| `S2-MAI-07` | MAI | `VERIFIED_NO_CODE_CHANGE`: existing `tests/test_source_owner_scope.py` covers private source/chunk visibility and cross-user run isolation. |
| `S2-CHUNG-01` | CHUNG | `DOC_ONLY`: rubric below defines relevance as an evidence-support judgment, separate from locator validity and semantic correctness. |
| `S2-CHUNG-02` | CHUNG | `DOC_ONLY`: fixed in-scope and absent-from-corpus cases are listed below without treating absence as a global product claim. |
| `S2-CHUNG-03` | CHUNG | `DOC_ONLY` plus the `S2-MAI-06` static check: existing 12-case calibration scenarios are referenced, not regenerated or edited. |
| `S2-CHUNG-04` | CHUNG | `DOC_ONLY`/`PENDING_HUMAN_REVIEW`: concise static relevance and gap conclusions are recorded below; no milestone or semantic approval is asserted. |

## S2-CHUNG-01 — evidence relevance rubric

The rubric is intentionally small and reviewable. It is not an LLM judge and
does not turn a valid chunk ID into a correctness score.

| Label | Meaning for the fixed corpus | Required handling |
| --- | --- | --- |
| `DIRECT` | The chunk states the requested fact or rule directly. | Eligible evidence for the claim, subject to human semantic review. |
| `SUPPORTING` | The chunk supplies a related definition or constraint but does not fully answer the request. | May support a partial answer; do not treat it as complete coverage. |
| `NOT_RELEVANT` | The chunk is available but does not support the requested fact, even if it shares a broad domain label. | Exclude from claim support. |
| `MISSING` | The fixed corpus contains no supporting chunk for the requested fact. | Return `NO_EVIDENCE`/`PARTIAL` as appropriate; do not infer or fabricate a citation. |
| `UNSCORED` | Locator/automation evidence exists, but correctness or faithfulness has not been manually reviewed. | Keep outside semantic or milestone claims. |

Locator validity answers “does this ID identify a supplied chunk?” Relevance
answers “does that chunk support this request?” Correctness and faithfulness
remain separate human-review dimensions.

## S2-CHUNG-02 — fixed in-scope and absent-from-corpus cases

The fixed corpus is a deliberately small M0 calibration corpus, so “out of
scope” here means absent from this evidence set, not unsupported by the wider
application or by future sources.

| Boundary | Fixed cases/content |
| --- | --- |
| In-scope: security | `M0-01` authentication identity; `M0-02` authorization permission; `M0-03` JWT claims versus server-side policy; `demo_security.md`. |
| In-scope: database | `M0-04` user-record storage; `M0-05` index review; `M0-06` transaction boundaries; `demo_database.md`. |
| In-scope: API/architecture | `M0-07` REST endpoints; `M0-08` API contract fields; `M0-09` explicit architectural dependencies; `demo_api.md`. |
| Absent from fixed corpus | `M0-10` production deployment region; `M0-11` password minimum length; `M0-12` monthly SLA percentage. These must remain missing-evidence cases for this calibration snapshot. |

The absent cases are useful negative controls: a domain-adjacent answer or a
fact known from another file must not be substituted for evidence that is not
in the fixed corpus.

## S2-CHUNG-03 — fixed calibration scenarios

The existing calibration fixture contains 12 unique IDs: nine
`expected_evidence=present` cases and three `expected_evidence=missing` cases.
The existing FakeProvider report is checked as a read-only artifact by the new
focused test. Its automated `locator_valid`, `evidence_behavior_ok`, and
`source_match` fields are `true` for every row, while both
`manual_correctness` and `manual_faithfulness` remain `UNSCORED` for every
row. This is wiring evidence only; the fixture and report bytes are unchanged.

## S2-CHUNG-04 — QA-reviewed relevance and gap conclusions

### Static relevance findings

1. The fixed security, database, and API chunks provide direct lexical support
   for the nine evidence-present queries. The focused retrieval test confirms
   the relevant fixed source ranks first for a security query.
2. A query for the production deployment region produces no retrieval hit at
   the configured minimum score. The static calibration report records the
   corresponding `NO_EVIDENCE` behavior without a citation.
3. The automated report confirms locator/source wiring, not answer quality.
   The explicit `UNSCORED` manual fields preserve that boundary.

### Gaps that remain open

1. The lexical retriever check is not a semantic relevance or recall@K
   measurement. Near-match, contradiction, negation, and multi-hop cases are
   not represented in this fixed M0 fixture.
2. No local Ollama run or target-machine resource measurement was performed in
   this task. FakeProvider output cannot promote M0 or any research milestone.
3. No human correctness/faithfulness review was performed here. A human
   reviewer must apply the rubric before any semantic or milestone claim.

### Review boundary

These conclusions are QA notes over fixed content, not self-approval. The
highest supported label is `STATIC_CONTRACT_EVIDENCE`; M0 semantic correctness
and milestone approval remain `PENDING_HUMAN_REVIEW` under project governance.

## Focused verification

New tests:

```text
tests/test_sprint2_quality.py — 5 passed in 1.89s
```

Existing baseline seam checks rerun in the assigned worktree:

```text
tests/test_budget.py tests/test_pipeline.py tests/test_source_store.py
tests/test_ollama_provider.py — 8 passed in 3.63s
```

Both commands used the repository's existing local virtual environment, pytest
cache disabled, and temporary stores. They did not invoke Ollama or an
experiment runner. The bundled workspace Python did not include pytest; this
is an environment note, not a product change.

## Delivery notes

- Changed files: `tests/test_sprint2_quality.py` and this report only.
- No dataset, gold, P/N/O, condition/profile, runtime, or product source file
  was changed.
- Task-specific branch: `codex/s2-mai-chung-quality-docs`.
- Task-specific commit IDs are reported in the parent handoff after the
  commits are created; `S2-MAI-05` and `S2-MAI-07` intentionally have no
  manufactured empty commit.
- No push or merge was performed.
