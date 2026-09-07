# Trace semantics closure

## O first divergence

The inaccurate `selected_evidence.reason=retained_shared` originated in
`ContextController.select_for_task`: the controller emitted that label before
`OverlapTracker.observe` had compared a later task. The tracker subsequently
computes `shared_evidence_ids` and `reused_from_task_ids` correctly. This was a
trace-label defect, not an O allocation or sharing-policy defect.

The minimal correction changes the pre-tracker label to `retained`; only the
tracker can later assert cross-task sharing. Focused test `4 passed` verifies
that a first local selection cannot claim shared evidence.

## Required meanings

- `retained`: selected for this task by bounded local selection; no cross-task claim.
- `retained_shared`: only when `OverlapTracker` records that stable evidence ID
  in `shared_evidence_ids` with a reuse source task.
- `exact_duplicate`, `overlapping_span`, `budget_exceeded`: O drop reasons,
  not interchangeable labels.
- P trace has `planning_retrieval` before `decomposition`.
- N trace records `KEEP`, `MERGE`, or rollback and preserves dependency validity.

Live O traces exercise shared retention and explicit drop reasons. No global
evidence removal or semantic merge was added.
