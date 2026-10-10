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
- Fake-provider wiring calibration and tests.

### Kiểm tra trong build environment

- `pytest`: 8 PASS.
- Fake calibration: 12 cases executed; expected evidence-present/missing behavior and expected source checks pass in the generated report.

### Chưa có bằng chứng

- Ollama/local model actually running on the target Windows laptop.
- Actual model JSON/citation behavior.
- Actual latency/RAM/VRAM/thermal.
- Manual correctness/faithfulness scores.
- Restart/restore from a real Git/LKG release on target laptop.
- Frozen model digest/tag from target machine.

=> Cần chạy `CODEX_M0_LOCAL_GATE_PROMPT.md` hoặc tự chạy `RUN_M0_CALIBRATION_LOCAL.ps1` trên laptop.
