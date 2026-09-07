# Frozen human-review rubric — M1 v1

This rubric is immutable for a pilot namespace. It joins each review to the
canonical ledger key `experiment_id|case_id|condition|repeat_index`; `run_id`
is supporting provenance only. A duplicate/raw attempt cannot replace the
canonical reviewed record.

| Field | Allowed value | Evidence boundary |
| --- | --- | --- |
| `sufficient_pass` | `PASS`, `FAIL`, `UNSCORED` | reviewer compares final answer to frozen case obligations; no model self-assessment |
| `faithfulness` | `PASS`, `FAIL`, `UNSCORED` | every material claim needs cited, allowed canonical evidence |
| `relevant_context` | `SUFFICIENT`, `INSUFFICIENT`, `UNSCORED` | reviewer judges selected context against frozen case, not retrieval score |
| `task_obligation_matches` | reviewed task-to-obligation IDs | input to deterministic Task Coverage; never copied from model claims |

Every non-`UNSCORED` decision requires reviewer ID, date, a short evidence
rationale, and cited evidence/task IDs. Disagreement remains separate reviews;
the runner never infers a majority or a score.
