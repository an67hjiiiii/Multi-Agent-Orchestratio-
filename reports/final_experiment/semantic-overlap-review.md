# Final dataset semantic-overlap review

This is a human-review aid, not a runtime artifact. Exact/near text checks are
static; the project owner approved semantic distinctness for all 30 groups on
2026-09-09 (`PROJECT_OWNER`).

| final scenario | primary archetype | nearest development case(s) | why this is structurally distinct | reviewer status |
|---|---|---|---|---|
| M1F-S01 | SIMPLE_SINGLE_OBLIGATION | M1-01, M1-02 | It asks for the intake conclusion and does not repeat the development definition question or collapse authorization into it. | HUMAN_APPROVED |
| M1F-S02 | SIMPLE_SINGLE_OBLIGATION | M1-02, M1-07 | The holdout is an audit/authority-boundary composition rather than a direct 'what does authorization check' prompt. | HUMAN_APPROVED |
| M1F-S03 | SIMPLE_SINGLE_OBLIGATION | M1-05, M1-11 | It isolates the invalid-request checkpoint while using a review context, not the development list question about all contract fields. | HUMAN_APPROVED |
| M1F-S04 | SIMPLE_SINGLE_OBLIGATION | M1-03 | It combines storage context with a follow-up review decision instead of paraphrasing the development query about which queries need indexes. | HUMAN_APPROVED |
| M1F-S05 | SIMPLE_SINGLE_OBLIGATION | M1-04 | The holdout frames an invariant and a write sequence rather than asking the same direct timing question. | HUMAN_APPROVED |
| M1F-S06 | MULTI_OBLIGATION_CROSS_DOMAIN | M1-06, M1-07, M1-14 | This is a new end-to-end protected-write composition spanning all three frozen domains, not a pair or trio copied from development. | HUMAN_APPROVED |
| M1F-S07 | MULTI_OBLIGATION_CROSS_DOMAIN | M1-07, M1-14 | It introduces malformed-request behavior alongside identity/permission, a new cross-domain structure rather than a development pair. | HUMAN_APPROVED |
| M1F-S08 | MULTI_OBLIGATION_CROSS_DOMAIN | M1-03, M1-05, M1-08 | It couples a search endpoint with input handling, a relationship not present in the development prompts. | HUMAN_APPROVED |
| M1F-S09 | MULTI_OBLIGATION_CROSS_DOMAIN | M1-06, M1-14 | The new unit of analysis is an authorized consistency-sensitive write, not the development request's loose list of requirements. | HUMAN_APPROVED |
| M1F-S10 | MULTI_OBLIGATION_CROSS_DOMAIN | M1-05, M1-06, M1-14, M1-15 | It creates a service-readiness review around a lifecycle rather than reusing any one development wording or pair. | HUMAN_APPROVED |
| M1F-S11 | DEPENDENCY_TASK_GRAPH | M1-09 | The required dependency is an explicit output contract (identity result consumed by permission), not merely the word 'first'. | HUMAN_APPROVED |
| M1F-S12 | DEPENDENCY_TASK_GRAPH | M1-03, M1-08 | The dependency names a concrete storage finding that constrains the second task, unlike the development ordering prompt. | HUMAN_APPROVED |
| M1F-S13 | DEPENDENCY_TASK_GRAPH | M1-05, M1-11 | It tests an output-to-input contract between validation and error handling, a relationship absent from the development cases. | HUMAN_APPROVED |
| M1F-S14 | DEPENDENCY_TASK_GRAPH | M1-09, M1-14 | It adds a three-stage security-to-database output chain; the development case has no explicit gate into the write task. | HUMAN_APPROVED |
| M1F-S15 | DEPENDENCY_TASK_GRAPH | M1-07, M1-14 | The dependency crosses API contract and database persistence with an explicit consumed artifact, not a simple multi-obligation list. | HUMAN_APPROVED |
| M1F-S16 | DUPLICATE_OVERLAPPING_OBLIGATION_N | M1-10 | The repeated obligation is embedded in a normalization decision and uses no development wording about repeating evidence. | HUMAN_APPROVED |
| M1F-S17 | DUPLICATE_OVERLAPPING_OBLIGATION_N | M1-05, M1-11 | It explicitly tests duplicate validation wording and asks for a normalization decision, not an answer listing API fields. | HUMAN_APPROVED |
| M1F-S18 | DUPLICATE_OVERLAPPING_OBLIGATION_N | M1-04 | The holdout asks the normalizer to distinguish a duplicate consistency clause from a separate access-path concern. | HUMAN_APPROVED |
| M1F-S19 | DUPLICATE_OVERLAPPING_OBLIGATION_N | M1-02, M1-07 | It tests canonical duplicate detection inside an access-plan request rather than asking the direct authorization definition. | HUMAN_APPROVED |
| M1F-S20 | DUPLICATE_OVERLAPPING_OBLIGATION_N | M1-07, M1-14 | This is a cross-domain normalization case with one true duplicate and two protected distinct obligations, not a paraphrase of either development case. | HUMAN_APPROVED |
| M1F-S21 | SHARED_OVERLAPPING_EVIDENCE_O | M1-10 | It tests per-task overlap allocation and reuse accounting, not repeated-evidence wording in a decomposition request. | HUMAN_APPROVED |
| M1F-S22 | SHARED_OVERLAPPING_EVIDENCE_O | M1-03, M1-08 | It changes the unit from a single index question to two per-task contexts with legitimate shared grounding. | HUMAN_APPROVED |
| M1F-S23 | SHARED_OVERLAPPING_EVIDENCE_O | M1-11 | It requires O's per-task overlap trace and shared-evidence retention rather than the development request's shared-evidence observation. | HUMAN_APPROVED |
| M1F-S24 | SHARED_OVERLAPPING_EVIDENCE_O | M1-07, M1-11 | It creates a protected-endpoint overlap allocation across two source domains, a new task/evidence shape. | HUMAN_APPROVED |
| M1F-S25 | SHARED_OVERLAPPING_EVIDENCE_O | M1-06, M1-14 | The holdout tests overlap metrics around one authorized write and distinguishes shared grounding from task merging. | HUMAN_APPROVED |
| M1F-S26 | PARTIAL_INTENTIONAL_NO_EVIDENCE | M1-12 | The holdout wraps the missing fact in an evidence-boundary audit rather than repeating the direct production-region question. | HUMAN_APPROVED |
| M1F-S27 | PARTIAL_INTENTIONAL_NO_EVIDENCE | M1-01, M1-13 | It combines one supported security fact with an intentionally absent policy field, rather than paraphrasing the missing-evidence question alone. | HUMAN_APPROVED |
| M1F-S28 | PARTIAL_INTENTIONAL_NO_EVIDENCE | M1-05, M1-15 | It pairs supported API contract behavior with an absent service-level commitment in a new two-part review. | HUMAN_APPROVED |
| M1F-S29 | PARTIAL_INTENTIONAL_NO_EVIDENCE | M1-04, M1-08 | The missing item is a concrete schema identifier combined with supported storage/transaction facts, not the development data-model ordering prompt. | HUMAN_APPROVED |
| M1F-S30 | PARTIAL_INTENTIONAL_NO_EVIDENCE | M1-02, M1-13, M1-14 | It tests an absent algorithm field alongside supported controls and explicitly guards against an unsupported JWT inference. | HUMAN_APPROVED |
