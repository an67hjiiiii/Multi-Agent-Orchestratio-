# Benchmark input approval

The manifest contains exactly 15 frozen `development_validation` request
inputs (`datasets/pilot/m1_dev_cases.json`, SHA256
`e2fe5472108fa3ed6456a50676f163cc3a31c2e6781bac2edc5b4343289b4bb3`).

Human owner decision: **APPROVED** as `m1-dev-pilot-v1`, an M1
development/validation pilot subset. This approval does **not** designate it
as the full M1 empirical benchmark.

All fifteen case-level semantic-gold decisions are **APPROVED by the human
owner**. The signed values in `gold-approval-packet/gold-template.csv` are
evaluation-only, remain tied to the frozen corpus, and must never be consumed
by generation. This approval is limited to development/validation evidence.
