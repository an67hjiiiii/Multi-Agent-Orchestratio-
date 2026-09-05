# NCKH — Kế hoạch 6 Sprint / 5 thành viên

## Nguyên tắc
- 6 Sprint × 2 tuần ≈ 12 tuần.
- 5 thành viên giữ vùng trách nhiệm chính xuyên suốt.
- Codex có thể chia nhỏ thành nhiều worker song song, nhưng mọi worker phải map về Sprint + Member owner.
- Mỗi task hoàn thành phải báo: INPUT, OUTPUT, FILES, TESTS, COMMIT, BLOCKERS.

## 5 thành viên
| Member | Vai trò chính |
|---|---|
| Member 1 | Leader + Backend/API + Integration |
| Member 2 | Frontend + UI/UX |
| Member 3 | Local LLM + RAG + Retrieval |
| Member 4 | Research Core P/N/O |
| Member 5 | Dataset + Evaluation + Testing + Documentation |

## Sprint 1 — Foundation
- M1: FastAPI structure, API base, config, integration
- M2: React + TypeScript + Vite + Tailwind, app shell
- M3: Ollama, qwen3:4b adapter, local inference checks
- M4: research module boundaries/skeleton only
- M5: Pytest/Vitest, quality checks, run docs
Deliverable: Foundation PASS.

## Sprint 2 — M0 Technical MVP
- M1: API, source/chat/run integration
- M2: Sources, Answer, Evidence, basic Metrics UI
- M3: ingestion, chunking, retrieval, Qdrant/local retrieval, citation
- M4: Vanilla RAG A, context budget, NO_EVIDENCE
- M5: 12 calibration cases, trace, metrics, M0 tests
Deliverable: M0_LOCAL_GATE_PASS.

## Sprint 3 — Planning + Task Decomposition
- M1: task API, pipeline wiring
- M2: Task UI
- M3: Planning Retrieval + Planning KB
- M4: Task Decomposer + task schema + dependency structure
- M5: Task Coverage metric + P tests + pilot
Deliverable: P-lite PASS.

## Sprint 4 — N + O + Multi-Agent
- M1: Registry, worker execution, integration
- M2: Agent/Profile UI, Context/Evidence UI
- M3: task-specific RAG
- M4: N-rules + O-lite
- M5: Duplicate Task Rate, Evidence Recall, Context metrics, N/O tests
Deliverable: A/B/C PASS.

## Sprint 5 — M2 Evaluation / Ablation
- M1: experiment runner, condition config
- M2: experiment/result comparison UI
- M3: retrieval stability + performance
- M4: C-P / C-N / C-O + full mechanism refinements
- M5: benchmark, grading, metrics, statistics, result export
Deliverable: A, B, C, C-P, C-N, C-O reproducible.

## Sprint 6 — Finalize
- M1: integration, bug fixing, release
- M2: UI polish, demo flow
- M3: performance, local setup, reproduction
- M4: mechanism review, failure analysis
- M5: final experiment, tables/charts, report, documentation
Deliverable: Code + Demo + Experiment Results + Report + Presentation.
