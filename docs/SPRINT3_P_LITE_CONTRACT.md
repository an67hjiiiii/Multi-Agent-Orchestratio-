# Sprint 3 P-lite contract

## Boundary

Sprint 3 implements planning retrieval and structured task decomposition only.
It is local-only and uses the existing Ollama adapter. It does not implement
N normalization, O context allocation, a DAG scheduler, parallel execution,
or a Human Review UI redesign.

M0 is `TECHNICAL_PASS`; its Human gate is `HUMAN_REVIEW_PENDING`. This state
does not approve M0 or create a release tag.

## Locked data contract

`PlanningKnowledgeItem`

- `id: str`
- `domain: str`
- `title: str`
- `content: str`
- `provenance: str`

`PlanningRetrievalResult`

- `request: str`
- `item_ids: list[str]`
- `scores: list[float] | None`
- `context: str`

`TaskItem`

- `task_id: str`
- `title: str`
- `objective: str`
- `expected_output: str`
- `domain: str`
- `role_profile: str`
- `depends_on: list[str]`
- `covers_obligations: list[str]`

`RequiredObligation`

- `obligation_id: str`
- `canonical_kind: CanonicalTaskDomain | None`
- `source_anchor: str`

`DecompositionResult`

- `request: str`
- `tasks: list[TaskItem]`
- `planning_evidence_ids: list[str]`
- `status: str`
- `warnings: list[str]`
- `required_obligations: list[RequiredObligation]`
- `covered_obligations: list[str]`
- `missing_obligations: list[str]`
- `repair_attempted: bool`
- `coverage_validation_reason: str | None`

The decomposer receives only the bounded planning context. It calls the
existing local adapter with `think=false` where supported, accepts structured
JSON, validates it, and performs at most one structured retry. Dependency
validation rejects unknown IDs and cycles. Planning evidence is guidance for
decomposition and is never answer-domain evidence.

## File ownership map

| Worker | Member | Exclusive production ownership |
|---|---:|---|
| Planning KB | 3 | `app/planning/kb.py`, `datasets/planning/p_lite_items.json` |
| Planning retrieval | 3 | `app/research/planning_retrieval.py` |
| Task schema | 4 | `app/research/task_schema.py` |
| Local decomposer | 4 | `app/research/decomposer.py` |
| Decomposition API | 1 | `app/api/schemas.py`, `app/api/router.py` |
| P-lite pipeline | 1 | `app/research/p_lite_pipeline.py` |
| Task inspection component | 2 | `frontend/src/components/TaskResultPanel.tsx` |
| Planning evidence component | 2 | `frontend/src/components/PlanningEvidencePanel.tsx` |
| Task Coverage metric | 5 | `app/evaluation/task_coverage.py` |
| Pilot contract and docs | 5 | `datasets/planning/p_lite_pilot_cases.json`, `docs/SPRINT3_P_LITE_PILOT.md` |

Each worker may add only its focused test file. Integration workers, created
after these commits are verified, own the shared wiring files.
