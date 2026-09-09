# Final Human Evaluation Protocol (frozen draft)

**Protocol version:** `human-evaluation-v1`
**Mode:** `EVALUATION_PROTOCOL_ONLY`
**Core changes:** none
**Ollama/experiment runs while preparing this packet:** `0`

## Gate and scope

The final benchmark and semantic gold are still `PENDING_HUMAN_APPROVAL`.
This document defines the review procedure; it does not approve, rewrite, or
inject gold into generation. The 30-group set is the proposed final experiment
set, distinct from the approved 15-case M1 development/validation subset. A
human owner must approve the dataset and gold before the final experiment can
run. On approval, record reviewer identity, approval date, dataset revision,
benchmark SHA-256, and gold SHA-256 in the freeze record; after that, do not
change the 30 groups without a new approval.

The research framing is fixed: complex multi-obligation request handling is
the primary problem; P is Retrieval-Guided Task Decomposition, N is
obligation-preserving Task Normalization, and O is Overlap-Aware Context
Allocation. A/B/C and the C-P/C-N/C-O ablations remain comparable. No model,
provider, prompt budget, corpus, evaluator, or case is changed to improve a
score. Human reviewers never see mechanism labels, condition labels, P/N/O
flags, model/provider, or a claimed winner.

## Predeclared human sample

The sample is frozen before any final output is reviewed:

- groups: `M1F-S01` through `M1F-S30` (30 groups);
- selected variant: the first frozen variant (`variant_order == 1`) in each
  group, independent of outputs (`human-review-v1` selection rule);
- conditions: `A`, `B`, `C`, `C-P`, `C-N`, `C-O` (six conditions);
- repeat: `1`;
- human semantic reviews: `30 × 1 × 6 = 180` outputs;
- automatic structural/runtime records: all final runs (expected 720 when the
  final runner executes all four variants and six conditions).

`reports/final_experiment/blinded_review_manifest.json` is the evaluator-only
source of truth. It contains exactly 180 unique blind IDs and a separate
`BLIND_ID → condition/canonical attempt` mapping. Before final inference,
canonical run IDs are intentionally null (`PENDING_FINAL_RUN`). The
reviewer-facing CSV is a schema template; it has no condition column and no
model/mechanism fields. A materialized packet may be populated only from the
immutable final outputs and permitted evaluator gold after the run.

## Blinding and review packet

Each reviewer receives, per blind ID, only: the frozen request, permitted
evaluator gold, canonical corpus evidence/evidence excerpts, final rendered
answer, and technical status needed to interpret an answer. The reviewer does
not receive condition, mechanism, P/N/O state, model/provider, run order,
latency, token count, or winner. Evaluator-only mapping and automatic metrics
remain outside the reviewer packet. Gold is used for semantic comparison by
the evaluator and is never passed to generation.

Reviewers must not infer unsupported facts. When the permitted evidence does
not support a requested fact, the correct behavior is to state the gap (or
`NO_EVIDENCE` when the status contract requires it), not to guess.

## Semantic scoring rubric

### A. Obligation coverage (per atomic obligation)

Score each gold obligation independently, then report the mean and the
obligation denominator `N`:

- `1.0` — obligation is correctly addressed with sufficient detail;
- `0.5` — obligation is recognized but materially incomplete, ambiguous, or
  only partly correct;
- `0.0` — omitted, contradicted, or incorrectly answered.

Coverage is about the request's obligations, not the number of generated
tasks. Distinct obligations remain distinct even when they share evidence.

### B. Answer quality (`0–3`)

- `0` — materially incorrect, unsafe, incoherent, or unusable;
- `1` — some useful content, but major omissions/errors prevent reliable use;
- `2` — mostly correct and usable with only minor omissions or clarity issues;
- `3` — correct, sufficiently complete for supported obligations, clear about
  limits, and directly useful.

### C. Semantic grounding/faithfulness (`0–2`)

- `0` — material claims are unsupported by permitted evidence or contradict it;
- `1` — mixed grounding: some claims are supported but a material portion is
  weakly supported, overclaimed, or incompletely bounded;
- `2` — every material claim is supported by permitted evidence, and missing
  facts are explicitly bounded rather than invented.

Citation locator validity is a separate automatic check and must not be used
to inflate this semantic score.

### D. Missing-information behavior

For gold cases with an intentional evidence gap, record `PASS` when the answer
explicitly identifies the unavailable fact and avoids inventing it, `PARTIAL`
when the gap is acknowledged but incompletely handled, and `FAIL` when the
answer fabricates the fact or presents unsupported certainty. Use `N/A` only
when the case has no missing-information expectation.

### E. Status appropriateness

Record `PASS` when `COMPLETE`, `PARTIAL`, or `NO_EVIDENCE` matches the evidence
and obligation outcome; `FAIL` when the status materially overclaims or hides
a supported/unsupported boundary. A justified `PARTIAL` is acceptable when
its missing information or explicit status reason is present.

## N and O review rules

For the five predeclared N-overlap groups (`M1F-S16`–`M1F-S20`), review both
redundant-task reduction and obligation preservation. Merging is correct only
for exact canonical duplicates; authentication vs authorization, validation
vs error handling, and other distinct obligations must remain separate.

For the five predeclared O-shared groups (`M1F-S21`–`M1F-S25`), review whether
legitimate shared evidence is retained for every task that needs it, while
unnecessary repeated evidence is safely dropped under the context budget. A
lower chunk count alone is not success: coverage, grounding, and answer
quality must remain adequate.

## Reviewer agreement

With two or more reviewers, double-score a predeclared overlap of about 20% of
the 180 outputs (the exact IDs are selected before unblinding) and calculate
weighted Cohen's kappa for ordinal answer-quality/grounding fields plus
agreement summaries for categorical missing-information/status fields. Resolve
disagreements by a documented adjudication rule without changing the frozen
gold. With one reviewer, report the single-reviewer limitation and do not
claim inter-rater reliability.

## Metric boundaries and research questions

Automatic metrics cover **all final runs** (expected `N=720`): terminal status,
latency, total/input/output tokens when available, LLM calls, citation locator
validity, task/dependency structure, P/N/O trace fields, failures, retrieval,
context/overlap metrics, and resource/runtime fields already supported by the
runner. Do not invent unavailable metrics.

Human semantic metrics cover only the **180-output subset**: obligation
coverage, answer quality, semantic grounding/faithfulness, missing-information
handling, and status appropriateness. Always report the two denominators
separately (`N=720` automatic; `N=180` human semantic).

The preregistered comparisons are:

- RQ1: `C` vs `C-P` (effect of P);
- RQ2: `A` vs `B` (decomposition/task-specific path);
- RQ3: `C` vs `C-N` (effect of N);
- RQ4: `C` vs `C-O` (effect of O);
- RQ5: `A` vs `B` vs `C` (overall comparison).

These are development/research comparisons defined before outputs; no
post-hoc hypothesis, significance claim, or self-grading is permitted.

## Freeze and stop conditions

Before final execution, validate the benchmark/gold hashes and the manifest's
180-row Cartesian mapping. If the human approval gate is still pending, stop:
`READY_TO_RUN_FINAL_EXPERIMENT = NO`. After approval, update only the approval
record and immutable hashes, then let the existing runner execute; do not put
gold in prompts. This task does not run Ollama or any experiment.

The legacy runner fixture that hard-codes an earlier M1/Pilot query is
classified `HISTORICAL_TEST_STALE` because the current frozen dataset revision
is different and the final runner behavior is unaffected. Do not alter the
dataset or production code to satisfy that historical assertion; revisit only
if a current final-run focused test fails.
