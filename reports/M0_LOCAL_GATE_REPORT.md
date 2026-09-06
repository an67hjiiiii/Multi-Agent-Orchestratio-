# NCKH S2 — M0 Citation Locator Root-Cause Fix

ROOT_CAUSE: Stage A — qwen3:4b generated malformed or truncated full chunk locators. The raw Ollama JSON was valid; parsed citation values were unchanged; citation validation correctly rejected them. SourceStore canonical IDs, source serialization, API transformation, frontend rendering, and output-token truncation were not the corruption stage.

FAILED_CASES_BEFORE: 8/9 evidence-present cases failed the citation contract; NO_EVIDENCE was correct in 3/3 cases.

| Case | Raw model citation | Parsed citation | Expected canonical chunk ID | Final pre-fix locator | Stage |
| --- | --- | --- | --- | --- | --- |
| M0-01 | `src_ecad6:0000` | `src_ecad6:0000` | `src_ecad6843b8fcb99b_c0000` | `src_ecad6:0000` | A — model output |
| M0-02 | `src_ecad6:0000` | `src_ecad6:0000` | `src_ecad6843b8fcb99b_c0000` | `src_ecad6:0000` | A — model output |
| M0-03 | `src_ecad6:0000` | `src_ecad6:0000` | `src_ecad6843b8fcb99b_c0000` | `src_ecad6:0000` | A — model output |
| M0-05 | `src_1055b8f:0` | `src_1055b8f:0` | `src_1055b8f580d99531_c0000` | `src_1055b8f:0` | A — model output |
| M0-06 | `src_1055b8f:0000` | `src_1055b8f:0000` | `src_1055b8f580d99531_c0000` | `src_1055b8f:0000` | A — model output |
| M0-07 | `src_c7f9:92b35e6b484c5_c0000` | `src_c7f9:92b35e6b484c5_c0000` | `src_c7f92b35e6b484c5_c0000` | `src_c7f9:92b35e6b484c5_c0000` | A — model output |
| M0-08 | `src_c7f92b35e6b484c5_c0100` | `src_c7f92b35e6b484c5_c0100` | `src_c7f92b35e6b484c5_c0000` | `src_c7f92b35e6b484c5_c0100` | A — model output |
| M0-09 | `src_c7f92b35e6b1484c5_c0000` | `src_c7f92b35e6b1484c5_c0000` | `src_c7f92b35e6b484c5_c0000` | `src_c7f92b35e6b1484c5_c0000` | A — model output |

DESIGN_FIX: Vanilla RAG now presents application-owned evidence keys (`E1`, `E2`, ...) and resolves them deterministically to canonical `SourceChunk.chunk_id` values before validation. Exact canonical IDs remain backward-compatible; unknown, malformed, and truncated values remain rejected. Calibration dataset/gold was unchanged (SHA-256 `c8184eb69656e12f6b7a6adf9a3f8ed6c96c4348b7251d2d73dda0d6e32302d9`).

FILES: `app/core/citations.py`; `app/research/vanilla.py`; `tests/test_retrieval_citations.py`; `config/releases/m0_candidate_manifest.json`; this report; `reports/calibration/m0_calibration_ollama_20260906T002640Z.json`; `reports/calibration/m0_calibration_ollama_20260906T002640Z.csv`; `data/m0_calibration/sources.json`; 12 raw files under `runs/m0_calibration/`.

FOCUSED_TESTS: `tests/test_retrieval_citations.py` — 9 passed, including malformed locator, truncated locator, evidence-key mapping, invalid citation rejection, backward-compatible canonical ID, and citation-free NO_EVIDENCE.

PYTEST: 66 passed, 2 existing deprecation warnings.

FRONTEND: `npm ci`, `npm test` — 10 passed, and `npm run build` — PASS. No frontend files changed.

LOCAL_LLM: PASS — `scripts/check_local_llm.py`; Ollama `0.33.3`; `qwen3:4b`; digest `359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7`; JSON mode and `think=false` verified.

CALIBRATION: 12/12 real Ollama cases completed once, serially; 9 evidence-present cases `COMPLETE`, 3 missing-evidence cases `NO_EVIDENCE`; automated pass `12/12`.

CITATION_LOCATOR: 9/9 evidence-present cases have valid canonical source/chunk locators and zero invalid citations. All locators resolve in the frozen SourceStore snapshot `corpus_ecf5fd8b529c02d5`.

NO_EVIDENCE: M0-10, M0-11, and M0-12 remain citation-free with no fabricated evidence and zero LLM calls.

RESTART_SMOKE: PASS — project served two graceful Uvicorn instances; after restart, one evidence case returned `COMPLETE` and its citation resolved through `/api/chunks/{chunk_id}`, one missing-evidence case returned `NO_EVIDENCE`, and both runs persisted.

MANIFEST: Updated `config/releases/m0_candidate_manifest.json`; schema `m0-release-v1`; commit identity `7a598222f6935a62a8c75024d1c0f466387b119c`; provider `ollama`; model `qwen3:4b`; config `0732341dbc931c1e`; corpus `corpus_ecf5fd8b529c02d5`; claim remains candidate-only until local gate approval.

COMMIT: `7a598222f6935a62a8c75024d1c0f466387b119c` — `fix(citations): build canonical source locators`.

TAG: Not created; Human gate approval is required before an agent may mark the gate approved or create a pass tag.

BLOCKERS: No M0 technical blocker remains. Human approval is pending. `manual_correctness` and `manual_faithfulness` remain `UNSCORED — Human review required`; no semantic self-grade was performed. qwen3:4b remains a calibration candidate, not a research-frozen model.

DECISION: M0_LOCAL_GATE_PARTIAL

HARD STOP: Do not start Sprint 3 / M1.
