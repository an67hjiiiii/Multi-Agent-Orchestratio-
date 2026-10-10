# Kế hoạch triển khai M0 → M2

## Nguyên tắc

- Một codebase, điều khiển bằng `IMPLEMENTATION_PROFILE=m0|m1|m2|dev`.
- Không gọi milestone DONE chỉ vì code đã tồn tại. Phải qua gate bằng local LLM thật trên máy mục tiêu.
- `dev` chỉ dùng để ráp trước các phần tương lai; số liệu `dev` không được đưa vào main experiment.
- Mỗi milestone có Last Known Good (LKG), manifest, raw runs và restore instructions.
- UI polish, HERA Experience, QLoRA, advanced reranker không nằm trên critical path.

---

## M0 — Technical MVP

### Mục tiêu

`Text source → chunk/index → Vanilla RAG A → answer + valid citation → source viewer → trace/metrics`

### Code bắt buộc

1. Local LLM adapter.
2. UTF-8 text/code/markdown ingestion.
3. Stable source/chunk IDs + corpus snapshot ID.
4. Vanilla RAG condition A.
5. Hard pre-call context budget.
6. Structured answer state `COMPLETE | PARTIAL | NO_EVIDENCE | FAILED`.
7. Citation validation against selected chunks.
8. Source/chunk viewer API + UI.
9. Run trace: model, profile, config hash, corpus snapshot, retrieval IDs, tokens, latency, RAM/VRAM best effort.
10. 12 calibration cases + CSV/JSON exporter.
11. Candidate release manifest generator.

### Trạng thái code hiện tại

Đã cài đặt trong bản `0.2.0-m0`. Fake calibration chỉ chứng minh wiring, chưa chứng minh M0 local.

### Gate M0

M0 chỉ DONE khi trên laptop mục tiêu:

- Ollama/local runtime chạy model đã chọn.
- 12/12 calibration case được chạy bằng provider `ollama`.
- Source/citation locator mở đúng.
- Case thiếu evidence không tạo citation giả.
- Token/context cap không bị bypass.
- Có runtime measurements thực.
- Có manual correctness/faithfulness review.
- Restart app từ release/manifest và chạy lại được.
- Không còn blocker P0/P1 đối với A.

### Không làm trước Gate M0

Không promote B/C hoặc main pilot. Có thể phát triển sau feature flag trên `dev`, nhưng không gọi M1.

---

## M1 — Research MVP

### Mục tiêu

`A/B/C` cùng codebase và cùng local model/corpus/hardware; C thực sự chạy `P-lite + N-rules + O-lite`.

### Code sẽ làm sau M0 candidate

1. **Decomposer v1**
   - strict JSON schema;
   - atomic obligations;
   - dependencies preserved;
   - invalid plan -> explicit failure/repair, không silent fallback.
2. **Versioned Planning KB + P-lite**
   - file-backed planning items;
   - version/hash;
   - relevance gate;
   - top-k/cap;
   - trace selected/fallback reason.
3. **Capability Assignment**
   - planner không tự quyết toàn bộ agent;
   - structured Registry 3 profiles;
   - deterministic capability matching + explicit fallback.
4. **N-rules v1**
   - exact duplicate;
   - conservative near duplicate;
   - preserve constraints/dependencies;
   - ambiguous -> KEEP.
5. **Task-specific RAG**
   - query per task;
   - dependency context only when supported;
   - provenance preserved.
6. **O-lite v1**
   - relevance per task;
   - exact + span duplicate removal;
   - per-task/whole-run budget;
   - selected/dropped reason;
   - shared evidence allowed across tasks.
7. **Worker/Synthesizer v1**
   - structured citations;
   - partial/no-evidence propagation;
   - synthesis cannot invent source IDs.
8. **M1 evaluation harness**
   - only A/B/C;
   - 15 preselected dev/validation requests × 3 = 45 runs minimum;
   - CSV/JSON ledger;
   - task/role/evidence/token/latency metrics;
   - manual rubric columns.
9. **UI**
   - Tasks / Profiles / Evidence / Context / Metrics / Raw;
   - no advanced visualization needed.

### Gate M1

- A/B/C all run without code edits between conditions.
- Same frozen local model/corpus/hardware.
- C trace proves P/N/O were actually executed.
- Minimum 45 pilot runs completed and scored.
- Missing evidence and overlap cases included.
- LKG restore works.

### Nếu trễ

Giữ P-lite + O-lite; giữ N rules-only; bỏ semantic N advanced, MMR, advanced verifier/UI. Không cắt pilot/evaluation.

---

## M2 — Core Complete

### Mục tiêu

Full research protocol with `A/B/C/C-P/C-N/C-O`, P/N/O full, complete DAG/state handling, frozen benchmark and reproducible experiment package.

### Code cần hoàn thiện

1. **P-full**
   - controlled Planning KB;
   - relevance/fallback calibration;
   - long/ambiguous input handling;
   - deterministic manifest/versioning.
2. **N-full**
   - semantic candidate generation;
   - safe MERGE/KEEP/NARROW decision;
   - requirement/dependency remapping;
   - ambiguity audit trace.
3. **O-full**
   - exact/span/semantic redundancy;
   - relevance + new-need coverage - redundancy;
   - diversity/MMR-like selection;
   - shared/private evidence accounting;
   - token budget allocation and redistribution;
   - preserve conflict/version/negation/numeric evidence.
4. **DAG/state executor**
   - data dependencies;
   - child retrieval after parent state when required;
   - BLOCKED/PARTIAL/FAILED propagation;
   - bounded retry;
   - serial physical generation by default.
5. **Six-condition config validation**
   - A/B/C/C-P/C-N/C-O;
   - full profile required for main test;
   - condition/flags mismatch rejected.
6. **Benchmark/evaluation package**
   - 120 request target;
   - frozen splits;
   - annotation schema;
   - canonical attempt ledger;
   - resume/checkpoint;
   - blinded grading packets.
7. **Metrics/statistics**
   - Task Coverage;
   - Duplicate Task Rate;
   - Role Assignment Accuracy;
   - Evidence Recall@K;
   - context overlap / relevant context ratio;
   - context/input/output tokens;
   - answer score / sufficient pass;
   - faithfulness;
   - LLM calls, latency, RAM/VRAM, failure/retry;
   - paired/clustered CI and failure taxonomy.
8. **Freeze/reproduction**
   - code/config/model/corpus/Planning KB/labels manifests;
   - `m2-test-ready` before test;
   - no tuning on test;
   - final reproduction package.

### Gate M2

M2 DONE only after main experiment, grading, statistics, ablation and failure analysis are complete. C does not need to beat baselines.

---

## Phân việc: ChatGPT vs Codex trên máy người dùng

### Tôi có thể làm trực tiếp ở đây

- Thiết kế/refactor code Python/FastAPI.
- Unit/integration tests bằng Fake Provider.
- Feature flags/config schemas.
- P/N/O algorithms and experiment runner code.
- Dataset schemas/templates, ledgers, report scripts.
- UI logic that does not require the user's desktop/browser state.
- Static reproducibility/manifest tooling.

### Phải chạy trên laptop thật / Codex local

- Kiểm tra GPU/driver/Ollama thực tế.
- Pull/run local model files.
- Benchmark latency/RAM/VRAM/thermal trên máy thật.
- Chọn/freeze model sau calibration.
- Chạy hàng chục/hàng nghìn local inference runs lâu dài.
- Human annotation/blind grading coordination.
- Git tag/commit trong repo thật của người dùng.
- Desktop visual QA nếu phụ thuộc môi trường browser/Windows.

---

## Thứ tự thực thi đề xuất

1. **Ngay bây giờ:** M0 code candidate + Fake tests.
2. **Trên laptop:** chạy M0 local gate bằng prompt bàn giao.
3. **Song song:** tiếp tục code M1 trên feature flags/dev profile, nhưng chưa promote.
4. Khi M0 local gate PASS: khóa LKG M0.
5. Hoàn thiện M1 code → 45-run pilot → LKG M1.
6. Chỉ sau M1 có số liệu thật mới quyết định calibration/complexity của P/N/O full cho M2.
7. M2 code/freeze → main experiment → analysis → LKG M2.
