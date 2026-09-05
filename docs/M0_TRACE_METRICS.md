# M0 trace and metrics contract

This document defines the minimum observability contract for the M0 Vanilla
RAG condition A. It describes what a run records; it does not promote M0 to
`DONE`. Unit tests, FakeProvider runs, and a generated candidate manifest are
wiring/reproducibility evidence only. The target-machine Ollama gate and human
review are still required.

## Run identity

Every persisted run should retain these identity fields together:

| Field | Meaning |
| --- | --- |
| `run_id` | Stable identifier for the persisted run artifact. |
| `created_at` | UTC run creation timestamp. |
| `condition` | `A` for M0; another condition is outside the M0 profile. |
| `implementation_profile` | Runtime profile, expected to be `m0`. |
| `provider` / `model` | Provider and model used by the run. `qwen3:4b` remains a calibration candidate. |
| `source_snapshot_id` | Content-derived snapshot of the source/chunk store used for retrieval. |
| `config_hash` | Hash of the effective runtime configuration. |
| `effective_config` | The resolved limits and flags used for the run. |
| `status` | Terminal state: `COMPLETE`, `PARTIAL`, `NO_EVIDENCE`, or `FAILED`. |

`source_snapshot_id`, `config_hash`, provider, model, and profile must be read
with the answer and citations. A result without these bindings is not a
reproducible M0 trace.

## Trace events

Events are timestamped records in the run's `events` array. The M0 A path
records at least:

- `run_started`: condition, provider/model, profile, source snapshot, config
  hash, and effective flags.
- `vanilla_retrieval`: candidate chunk IDs, selected chunk IDs, and any
  budget-dropped chunks.
- `run_finished` or `run_failed`: the terminal state and failure category.

The selected chunk IDs must be the same IDs used by citation validation. A
source name alone is not sufficient provenance. If a trace is exported outside
the local workspace, inspect error messages and remove any credential or
provider-response material first.

## Metrics

The persisted `metrics` object uses the following meanings:

| Metric | Meaning and boundary |
| --- | --- |
| `llm_calls` | Provider results counted by the application. |
| `input_tokens`, `output_tokens` | Provider-reported usage; these are authoritative when available. |
| `total_tokens` | `input_tokens + output_tokens`. |
| `context_tokens_est` | Local pre-call token estimate for selected source text; not provider billing usage. |
| `context_chars` | Character count of selected source text. |
| `retrieved_chunks`, `selected_chunks`, `dropped_chunks` | Retrieval and hard-budget accounting. |
| `retrieval_latency_ms` | Time spent in lexical retrieval calls. |
| `generation_latency_ms` | Time accumulated around generation calls. |
| `latency_ms` | End-to-end time from run start through finalization, including retrieval and generation. |
| `citations_emitted`, `citations_valid` | Locator citation counts before and after validation. |
| `citation_locator_validity` | `citations_valid / citations_emitted`, or `null` when no citation was emitted. |
| `peak_rss_mb` | Largest of the process RSS samples observed at run start and finalization. It is not a continuous profiler peak. |
| `gpu_memory_mb` | Best-effort final NVIDIA device memory-used sample; `null` is valid when unavailable. |

The telemetry helpers in `app/core/telemetry.py` never make a run fail. They
return finite, non-negative MiB values when a measurement is usable and
`None` otherwise. The GPU helper reports the largest value returned for the
visible devices; it is not a per-process allocation measurement.

Zero is a measured value and `null` is unavailable/not applicable. Do not
replace unavailable latency, memory, or citation values with zero merely to
make an export complete.

## Candidate manifest

Generate the candidate release manifest after the code/config/corpus used for
the intended check is present:

```powershell
\.venv\Scripts\python.exe scripts\create_m0_manifest.py
```

The exporter is import-safe and writes
`config/releases/m0_candidate_manifest.json` only when run as a script. The
manifest records:

- schema, UTC creation time, M0/A boundary, and candidate-only claim status;
- effective runtime configuration and `config_hash`;
- model candidate status (`research_frozen: false`);
- Git commit/dirty state and SHA-256 hashes for relevant code/config/case/docs
  inputs;
- corpus snapshot ID and whether a local source-store file is present; and
- this trace/metrics contract.

`APP_DATA_DIR` may point to the source-store directory used for the manifest.
The path itself is not written into the manifest. An empty or absent store is
not calibration evidence. The manifest is a binding aid for a later local
gate, not proof of local inference, citation faithfulness, latency, hardware
behavior, restart/restore, or milestone completion.

## QA boundary

The focused checks in `tests/test_m0_manifest.py` cover manifest construction,
hashes, import safety, and best-effort telemetry behavior. They do not call
Ollama and do not execute the 12-case calibration. M0 completion additionally
requires the bounded target-laptop local gate: real Ollama inference, all 12
cases, citation/source smoke checks, runtime measurements, manual correctness
and faithfulness review, and restart/restore evidence.
