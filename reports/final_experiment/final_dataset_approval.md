# Final experiment dataset approval

Status: **PENDING_HUMAN_APPROVAL**.

The final benchmark is frozen as 30 genuinely held-out scenario groups with four variants per group (120 requests) in `datasets/final/final_benchmark_v1.json`. The draft gold is scenario-level only (one row per group, no task or obligation annotations) in `datasets/final/final_gold_v1.json`.

## Human approval packet

- `reports/final_experiment/scenario-gold-template.csv`: 30 review rows; all reviewer fields are blank and all statuses are `PENDING_HUMAN_APPROVAL`.
- `reports/final_experiment/corpus-evidence-manifest.json`: metadata-only resolver for the frozen `m1-pilot-authorized-v1` corpus.
- `reports/final_experiment/human-review-checklist.md`: detailed group/variant checklist.

## Required review

The human reviewer must inspect all four variants in every group, confirm role/domain labels and corpus evidence, and verify explicit missing-information cases. Empty evidence is allowed only for a recorded `expected_missing_information` target. Reviewer identity, notes, and approval date remain blank until independent review. No model/Ollama run has been performed, and no agent may self-approve semantic gold.

Static validation is provided by `scripts/validate_m1_final_dataset.py`; it checks IDs/counts, development exact/near-text exclusion, evidence resolver references, vocabulary, scenario-only gold shape, blank approval fields, and runtime source isolation.
