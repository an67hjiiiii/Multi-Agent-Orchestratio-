# O live acceptance — local Ollama only

| Case | Run | Observed trace | Result |
| --- | --- | --- | --- |
| O1 legitimate shared evidence | `run_2dad76ab399d` | task two records a selected stable ID in `shared_evidence_ids` and `reused_from_task_ids` from T1 | PASS: necessary authentication/authorization evidence retained across tasks |
| O2 duplicate / contained overlap | `run_8cf2feaa5d70` | contained spans `c0001`–`c0005` dropped as `overlapping_span`; selected evidence remains available to both tasks | PASS: no global removal and shared context retained |
| O3 budget pressure | `run_0690b3f7b0c5` | each task selected three estimated-400-token chunks (1200) and dropped three as `budget_exceeded` under the 1500 cap; task two shared all three with T1 | PASS: bounded per-task context plus explicit shared reuse |

`run_0690b3f7b0c5` is terminal `PARTIAL`, but the P/N/O structural traces,
bounded selection, drop reasons, and citations are recorded. It is not silently
treated as a quality PASS.
