# M1 final dataset readiness

Status: **HUMAN_APPROVED**. The project owner approved all 30 scenario groups
on 2026-09-09; this document records the frozen input/gold boundary and is not
an execution report or milestone result.

## Frozen input and gold boundary

- `datasets/final/final_benchmark_v1.json` contains 30 scenario groups with four
  stable variants each (120 frozen requests) and `dataset_revision` set to
  `FINAL_DATASET_V2_TARGETED_REWORK`.
- Holdout definition: held-out request / structure / composition set over the
  frozen corpus; underlying knowledge facts are not claimed to be unseen.
- `datasets/final/final_gold_v1.json` contains one scenario-level row per group,
  including archetype, status, domain scope, evidence, and mechanism
  expectations. It has no case-level gold; approval is recorded externally so
  the approved file bytes and hashes remain unchanged.
- `reports/final_experiment/evidence-review-packet.md` is evaluator-only and
  contains exact frozen corpus excerpts; it must never enter generation.
- `reports/final_experiment/final_dataset_v2_human_review.md` is the compact
  30-scenario review packet; variants inherit their scenario gold.
- `reports/final_experiment/semantic-overlap-review.md` records the static and
  human semantic holdout boundary.

## Static validation

Run:

```powershell
$pyExe = 'C:\Users\Viet Anh\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $pyExe scripts/validate_m1_final_dataset.py
```

The validator checks 30×4 counts, stable IDs, exact six-archetype distribution,
meaningful cross-domain groups, development exclusion, evidence references,
role/domain vocabulary, scenario-level gold fields, N/O/dependency expectations,
packet/overlap/evidence review coverage, blank Human approval fields, and static
gold isolation. It performs no model/provider call and does not run the runner.

## Owner approval and remaining boundary

- reviewer/owner: `PROJECT_OWNER`
- approved_at: `2026-09-09`
- semantic review: `30/30 scenario groups PASS`
- dataset SHA-256: `553b7e4de97bb3063d5f8f22994f368021b12a1439d8e4ea3d94b33dcbcd08ac`
- gold SHA-256: `558f96f77aeddbee3dd815fdb09ea8c5e30c59988ef902bd0498b0e60122ce8d`
- semantics changed after approval: `NONE`

The dataset/gold freeze gate is satisfied. No final experiment has run in this
step; execution remains a separate, explicitly authorized action and this
approval does not claim empirical quality or milestone completion.
