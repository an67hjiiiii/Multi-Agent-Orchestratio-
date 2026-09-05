# M0 status — code candidate

## Kết luận hiện tại

`M0 CODE CANDIDATE READY`, nhưng **M0 chưa được phép đánh dấu DONE**.

### Đã có

- Profile `m0` chỉ cho condition A.
- Vanilla RAG A one-generation answer path.
- UTF-8 ingestion + stable source/chunk IDs.
- Corpus snapshot ID + runtime config hash.
- Hard context token proxy cap.
- `COMPLETE/PARTIAL/NO_EVIDENCE/FAILED` state.
- Machine citation locator validation.
- Source/chunk viewer API and clickable UI citations.
- Basic retrieval/generation/E2E latency.
- Provider token usage + LLM call count.
- Process RSS and best-effort NVIDIA memory metric.
- Terminal failure run persisted.
- 12-case calibration runner.
- Candidate release manifest generator.
- Import-safe candidate manifest export with code/config/case hashes, Git
  identity, corpus presence, and an explicit trace/metrics contract.
- Fake-provider wiring calibration and tests.

## Trace/metrics QA boundary

M0 traces bind the answer to `run_id`, condition A, implementation profile,
provider/model, source snapshot, config hash, effective configuration, terminal
status, retrieval provenance, and the persisted metrics object. The metrics
contract is documented in `docs/M0_TRACE_METRICS.md`.

The candidate manifest is a reproducibility artifact only. Its
`claim_status` remains `CANDIDATE_ONLY_UNTIL_LOCAL_GATE_PASSES`; a clean hash,
unit test, or FakeProvider run cannot promote M0. `null` RAM/VRAM values are
valid when the host cannot provide a measurement, and the documented
start/finalization sampling boundary must not be reported as continuous
profiling.

### Kiểm tra trong build environment

- Previously recorded candidate baseline: `pytest`: 8 PASS; this is not a
  post-change result for the trace/manifest slice.
- Focused coverage for this slice is `tests/test_m0_manifest.py`; execute it
  in an environment with the repository test dependencies installed.
- Fake calibration: 12 cases executed; expected evidence-present/missing behavior and expected source checks pass in the generated report.

### Chưa có bằng chứng

- Ollama/local model actually running on the target Windows laptop.
- Actual model JSON/citation behavior.
- Actual latency/RAM/VRAM/thermal.
- Manual correctness/faithfulness scores.
- Restart/restore from a real Git/LKG release on target laptop.
- Frozen model digest/tag from target machine.

=> Cần chạy `CODEX_M0_LOCAL_GATE_PROMPT.md` hoặc tự chạy `RUN_M0_CALIBRATION_LOCAL.ps1` trên laptop.
