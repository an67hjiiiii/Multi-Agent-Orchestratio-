# M1 metric inventory and measurement contract

This inventory distinguishes recorded run facts from derived or human-reviewed
claims. A missing input produces the declared unavailable state; it is never
silently changed to zero or PASS.

| Metric | Classification | Inputs / formula | Canonical output and scope | Missing-data behavior |
| --- | --- | --- | --- | --- |
| terminal status | AUTOMATED_CANONICAL | `RunResult.status` | `COMPLETE`, `PARTIAL`, `NO_EVIDENCE`, `FAILED`; all A/B/C | no terminal record is a gate failure |
| LLM calls, input/output/total tokens | AUTOMATED_CANONICAL | `RunMetrics` provider usage; total=input+output | per run and aggregate | usage unavailable is explicitly recorded |
| latency, retrieval/generation latency | AUTOMATED_CANONICAL | `RunMetrics` timers | milliseconds per run | `null` when not measured |
| RAM / VRAM | AUTOMATED_CANONICAL | `peak_rss_mb`, `gpu_memory_mb` | per run when collector supplies them | `null`, never inferred |
| context tokens/chars and chunks | AUTOMATED_CANONICAL | `RunMetrics.context_*`, selected/retrieved/dropped | per run / task trace | unavailable must be explicit |
| citation validity / locator validity | AUTOMATED_CANONICAL | valid citations ÷ emitted citations | `citation_locator_validity`; evidence-bearing answers | `null` when no citations are emitted |
| failure status | AUTOMATED_CANONICAL | terminal record + error event | failure/retry facts | absent retry counter is `NOT_RECORDED`, not zero retries |
| duplicate tasks removed | AUTOMATED_CANONICAL | N normalization event and metric | count for C/N-on runs | `0` only when N ran and removed none |
| duplicate task rate | AUTOMATED_DERIVED | removed / (tasks_after + removed) | case/condition value when normalization event exists | `UNDEFINED` without plan before/after |
| overlap/reuse ratio | AUTOMATED_DERIVED | repeated selected IDs / all selected ID occurrences | task and run aggregate | `UNDEFINED` without selected IDs |
| Task Coverage | HUMAN_REVIEW | frozen obligations + independent task-to-obligation annotation | `calculate_task_coverage` result | `UNDEFINED` without gold or review |
| Evidence Recall@K | BLOCKED | frozen gold evidence IDs + ranked retrieval IDs | evaluation metric | blocked: frozen gold evidence absent |
| Role Assignment Accuracy | BLOCKED | frozen role labels + independent role judgment | evaluation metric | blocked: approved role gold absent |
| relevant-context ratio | HUMAN_REVIEW | selected evidence + relevance labels | per task / run | `UNSCORED` without review |
| answer quality / SufficientPass | HUMAN_REVIEW | frozen obligations + reviewer rubric | case-condition result | `UNSCORED` pending review |
| faithfulness | HUMAN_REVIEW | rendered claims/citations + allowed evidence | case-condition result | `UNSCORED` pending review |

The M1 runner ledger provides immutable canonical/duplicate classification and
atomic checkpoints, but it does not presently add every derived or human metric
to its rows. That is a closure blocker for a full empirical M1 claim, not an
invitation to fabricate backfilled values.
