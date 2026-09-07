# Final bounded A/B/C smoke

Validation group: `m1-freeze-abc-final-v1`; one case (`M1-01`), one repeat, serial local Ollama `qwen3:4b`, freeze candidate `54a5e0eb28bc73b385ebb52ae137d78e67eb3f914c3c43f3db6eb63c8fdb863a`.

| Condition | Canonical run | Status | LLM calls | Tokens | Latency ms | Citation validity |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| A | `run_9218617b40d0` | COMPLETE | 1 | 287 | 9747 | 1.0 |
| B | `run_19b1bac175a9` | COMPLETE | 3 | 1376 | 27461 | 1.0 |
| C | `run_0f60fe11f9b4` | COMPLETE | 3 | 1667 | 33766 | 1.0 |

A trace is vanilla only. B contains decomposition and task retrieval with P/N/O off. C contains planning retrieval before decomposition, normalization, task retrieval, and overlap summary. All records use provider `ollama`, model `qwen3:4b`, the same freeze ID, and canonical metric snapshots. Gold was not available to generation. The namespace has no remaining `.pilot.lock`.

| Automated metric | A | B | C | Status |
| --- | --- | --- | --- | --- |
| terminal_status | COMPLETE | COMPLETE | COMPLETE | PASS |
| llm_calls | 1 | 3 | 3 | PASS |
| total_tokens | 287 | 1376 | 1667 | PASS |
| latency_ms | 9747 | 27461 | 33766 | PASS |
| peak_rss_mb | 42.33 | 44.77 | 45.17 | PASS |
| gpu_memory_mb | 2323 | 2323 | 2323 | PASS |
| context_tokens_est | 100 | 100 | 100 | PASS |
| citation_locator_validity | 1.0 | 1.0 | 1.0 | PASS |
| duplicate_tasks_removed | N/A | N/A | 0 | PASS |
