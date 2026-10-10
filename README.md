# Local Multi-Agent RAG — M0 Candidate / M1-M2 Base

Research codebase for:

**Retrieval-Guided Task Decomposition and Overlap-Aware Context Allocation for Resource-Constrained Local Multi-Agent RAG**

This repository is a clean codebase. Legacy Adaptive Orchestrator research semantics are not part of the new core.

## Current status

- **S0 wiring:** available under `IMPLEMENTATION_PROFILE=dev` for engineering only.
- **M0 code candidate:** implemented.
- **M0 DONE:** **not yet** — must pass the local Ollama gate on the target laptop.
- **M1/M2:** planned in `docs/M0_M2_EXECUTION_PLAN.md`; future code stays behind implementation profiles/feature flags.

## M0 code already present

- Local FastAPI web app.
- Vanilla RAG condition A.
- UTF-8 source ingestion.
- Stable source/chunk IDs + corpus snapshot.
- Citation locator validation + clickable source excerpt viewer.
- Hard pre-call context budget.
- `COMPLETE/PARTIAL/NO_EVIDENCE/FAILED` states.
- Run trace, config hash, token/latency/RAM/VRAM metrics.
- Fake Provider for wiring tests.
- Ollama Provider for real local inference.
- 12-case M0 calibration runner.
- Candidate release manifest generator.


## New repository bootstrap

This package is intentionally distributed without `.git`. On the target Windows laptop, extract it to a real project folder (recommended `D:\\Local-Multi-Agent-RAG`) and run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\BOOTSTRAP_NEW_REPO.ps1
```

See `docs/REPO_BOOTSTRAP_AND_WORKFLOW.md`.

## First run on Windows

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\START_WINDOWS.ps1
```

Then open `http://127.0.0.1:8000`.

The product runtime uses PostgreSQL as its authoritative store. Configure
`APP_STORAGE_BACKEND=postgres` and a PostgreSQL 16 `DATABASE_URL`, then apply
the schema with `python -m alembic upgrade head` before starting the app. The
JSON-backed stores are available only when `APP_STORAGE_BACKEND=file` is set
explicitly for isolated test/demo use.

This default path is suitable for wiring/demo. **Fake provider is not evidence that M0 is DONE.**

## Run M0 with local Ollama

After Ollama and the selected model are available:

```powershell
.\START_M0_LOCAL.ps1
```

Run the full M0 target-laptop calibration:

```powershell
.\RUN_M0_CALIBRATION_LOCAL.ps1
```

Or give Codex the instructions in:

`docs/CODEX_M0_LOCAL_GATE_PROMPT.md`

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Important

Do not report M0/M1/M2 as complete based on Fake Provider, unit tests, or UI screenshots alone. Milestone promotion follows the gates in the research plan and `docs/M0_M2_EXECUTION_PLAN.md`.
