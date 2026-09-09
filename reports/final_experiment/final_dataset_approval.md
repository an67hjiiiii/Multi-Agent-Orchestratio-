# Final dataset v2 targeted rework — human approval packet

Status: **HUMAN_APPROVED** (owner approval recorded 2026-09-09; 30/30
scenario groups PASS).

This packet reuses the existing final dataset path and runner contract while
rebalancing the 30 scenario groups into six explicit archetypes (five groups
each). It is the approved held-out final-experiment input, not a runtime
generation input.

## Frozen set and intended role

- 30 scenario groups × four semantically equivalent variants = 120 requests.
- Intended role: final M1 experiment input, with semantic Human review complete.
- Holdout definition: held-out request / structure / composition set over the
  frozen corpus; the underlying knowledge facts are not claimed to be unseen.
- Development set exclusion remains static plus a separate semantic-overlap
  review table. The set is approved for execution by the owner; no final
  experiment has been run in this freeze step.
- The runner remains unchanged and still loads the existing v1-compatible
  request schema; `dataset_revision` records this v2 targeted rework.

## Archetype distribution

| archetype | groups |
|---|---:|
| SIMPLE_SINGLE_OBLIGATION | 5 |
| MULTI_OBLIGATION_CROSS_DOMAIN | 5 |
| DEPENDENCY_TASK_GRAPH | 5 |
| DUPLICATE_OVERLAPPING_OBLIGATION_N | 5 |
| SHARED_OVERLAPPING_EVIDENCE_O | 5 |
| PARTIAL_INTENTIONAL_NO_EVIDENCE | 5 |

S06–S10 are the required meaningful cross-domain groups. N and O groups carry
explicit normalization/overlap expectations; dependency groups carry explicit
output-to-input ordering. Intentional missing-evidence cases state exactly what
must remain unknown.

All 30 prior groups were replaced because the previous distribution was
paraphrase-heavy and did not carry the required six-archetype contract. No
scenario group is reused unchanged.

## Review artifacts

- `scenario-gold-template.csv`: one approved scenario row per group.
- `final_dataset_v2_human_review.md`: one compact scenario-level review bundle
  with all 30 groups and four variants per group.
- `evidence-review-packet.md`: exact frozen chunk text for evaluator-only review.
- `semantic-overlap-review.md`: nearest development case(s) and a distinctness
  rationale for every final scenario.
- `corpus-evidence-manifest.json`: metadata resolver for the same three frozen
  chunks.

Gold fields remain scenario-level and independent of model outputs. The
approved benchmark/gold bytes are frozen at the exact hashes below; the source
JSON is not rewritten with approval metadata because doing so would change the
approved hashes. Approval is recorded in this packet, the canonical project
state, and the manifests. No gold is imported into generation.

## Owner approval and freeze record

- reviewer/owner: `PROJECT_OWNER`
- approved_at: `2026-09-09`
- scenario groups: `30/30 PASS`
- dataset revision: `FINAL_DATASET_V2_TARGETED_REWORK`
- dataset SHA-256: `553b7e4de97bb3063d5f8f22994f368021b12a1439d8e4ea3d94b33dcbcd08ac`
- gold SHA-256: `558f96f77aeddbee3dd815fdb09ea8c5e30c59988ef902bd0498b0e60122ce8d`
- semantic changes after approval: `NONE`
- freeze status: `FROZEN`

## Human decisions requested

Human review is complete for all scenarios. Preserve obligations/status, role
and domain scope, evidence references, answer points, missing-information
behavior, and dependency/normalization/overlap semantics exactly. Do not infer
facts absent from the frozen corpus or alter the approved files without a new
owner approval.
