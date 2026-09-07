# Automated metric to ledger mapping

`PilotLedger.append` materializes `metric_snapshot` for every canonical or
duplicate attempt. Snapshot schema is `m1-metric-contract-v1`; it is keyed by
the ledger attempt `key`, with `run_id` retained as raw provenance.

| Metric | Source/formula | Conditions | Test evidence |
| --- | --- | --- | --- |
| terminal, calls, tokens, latency, RAM/VRAM | `RunMetrics` / terminal record | A/B/C | `test_pilot_ledger` |
| context/retrieval/selection/drop/citation | `RunMetrics` | A/B/C | `test_pilot_ledger` |
| duplicate count/rate | normalization trace; removed/(after+removed) | C only | C value, A/B `null` |
| overlap reuse ratio | shared selected occurrences / selected occurrences | C only | C value, A/B `null` |
| failure stage | `run_failed` / `runner_failed` event | A/B/C | explicit null when absent |
| retry count | no current runner counter | A/B/C | literal `NOT_RECORDED`, never inferred as zero |

Human/gold metrics are deliberately excluded from this snapshot.
