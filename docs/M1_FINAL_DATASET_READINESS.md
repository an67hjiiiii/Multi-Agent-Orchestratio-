# M1 final dataset readiness

Status: **PENDING_HUMAN_APPROVAL**. This document records readiness evidence
for the final experiment input set; it is not an execution report or milestone
approval.

## Frozen input and gold boundary

- `datasets/final/final_benchmark_v1.json` contains 30 scenario groups
  with four stable variants each (120 frozen requests).
- `datasets/final/final_gold_v1.json` contains exactly one scenario-level
  draft row per group. It has no task IDs, obligation IDs, or case-level gold.
- `reports/final_experiment/scenario-gold-template.csv` is a human review
  sheet; all rows remain `PENDING_HUMAN_APPROVAL` with blank reviewer fields.
- The evidence resolver lists only canonical chunk metadata for the frozen
  `m1-pilot-authorized-v1` corpus. Empty evidence is valid only when the row
  records an explicit missing-information target.

The final requests are held out from the 15-case development file by exact
text and conservative near-text checks. These static checks do not establish
semantic non-paraphrase; the independent human review remains required.

## Static validation

Run:

```powershell
$pyExe = 'C:\Users\Viet Anh\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $pyExe scripts/validate_m1_final_dataset.py
```

The validator checks schema/counts, stable IDs, four variants per group,
development exclusion, corpus evidence references, registered role/domain
vocabulary, scenario-only gold shape, blank Human approval fields, and static
gold isolation across `app/research` and `app/providers`. It performs no
model/provider call and does not run the M1 runner.

## Remaining blocker

No agent may approve semantic gold. A human reviewer must inspect all variants,
resolve evidence, verify missing-evidence cases, and record independent
reviewer identity/date before any final experiment execution.
