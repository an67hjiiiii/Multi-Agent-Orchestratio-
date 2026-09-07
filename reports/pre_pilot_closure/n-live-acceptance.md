# N live acceptance — local Ollama only

All cases used `qwen3:4b` through the allowlisted local Ollama adapter and
fresh, immutable namespaces. No FakeProvider result is used as acceptance
evidence.

| Case | Run | Status | N trace | Result |
| --- | --- | --- | --- | --- |
| N1 exact duplicate probe | `run_8a3eb278b788` | PARTIAL | `KEEP T1`; `MERGE T2 into T1`, reason `exact_canonical_duplicate`; removed `1` | PASS: true duplicate normalized while raw task provenance remains in trace |
| N2 distinct obligations | `run_2dad76ab399d` | COMPLETE | `KEEP T1`, `KEEP T2`; authentication and authorization canonical fields differ | PASS: no semantic merge |
| N1 superficially overlapping request | `run_6b3affe79667` | COMPLETE | `KEEP T1`, `KEEP T2`; second task included a distinct re-verification obligation/dependency | PASS: conservative policy preserved a distinct obligation |

Namespaces: `runs/pre_pilot_closure/live-acceptance-v1/` and
`runs/pre_pilot_closure/live-acceptance-n1-o3-v1/`. The PARTIAL output on the
true-duplicate run is terminal evidence; it does not erase the independently
observed N normalization event.
