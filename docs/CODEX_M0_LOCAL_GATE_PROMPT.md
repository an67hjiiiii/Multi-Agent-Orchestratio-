# CAP1 LEAN EXECUTION — M0 Local Gate

TASK:
M0-A — Target-Laptop Local Ollama Integration + Calibration Gate

MODEL:
GPT-5.6 Luna — Chuyên sâu

MODE:
DIRECT / DIAGNOSE_FIRST only on an observed blocker

TEST TIER:
T3 — milestone integration gate

WEB:
OFF

SUBAGENTS:
OFF

## MISSION

Validate the existing M0 code candidate on the real Windows laptop with the already-working local Ollama `qwen3:4b` model. Make only blocker fixes required for M0. Do not implement M1/M2 and do not redesign the research architecture.

## KNOWN VERIFIED EVIDENCE

Already manually verified on this laptop:

```text
RTX 3050 Laptop GPU, 4 GB dedicated VRAM
16 GB class system RAM
ollama run qwen3:4b -> PASS
Ollama /api/chat -> PASS
think=false through API -> PASS
format=json through API -> PASS
final JSON example -> {"status":"ok","message":"local llm working"}
```

Do not redownload or switch models unless the actual M0 calibration proves a blocker.

## SOURCE OF TRUTH

Read only these first:

```text
README.md
RUN_ME_FIRST.md
docs/M0_STATUS.md
docs/M0_M2_EXECUTION_PLAN.md
app/providers/ollama.py
scripts/check_local_llm.py
scripts/run_m0_calibration.py
datasets/calibration/m0_cases.json
```

Then inspect only the closest production/test file for an observed failure.

Do not audit the legacy Adaptive Agent project.
Do not scan the repository broadly.
Maximum one targeted `rg` per missing symbol.

## PRE-FLIGHT

Run:

```powershell
git status --short
git branch --show-current
git rev-parse --short HEAD
```

Require a clean or explainable working tree. Record the starting HEAD.

Then record:

```powershell
python --version
py --version
ollama --version
ollama list
nvidia-smi
```

Do not repeat manual hardware discovery beyond what is needed for the final measurements.

## OWNERSHIP

Preferred allowed files if a blocker requires code changes:

```text
app/providers/ollama.py
app/research/vanilla.py
app/research/pipeline.py
app/core/citations.py
app/core/telemetry.py
app/retrieval/text.py
scripts/check_local_llm.py
scripts/run_m0_calibration.py
scripts/create_m0_manifest.py
tests/test_*.py
docs/M0_BLOCKER_FIXES.md
```

Production change budget: <= 2 files preferred, maximum 3 with evidence.
Test change budget: <= 1 focused test file preferred.
Dependencies: 0 unless a hard blocker is proven.

Do not modify M1/M2 mechanisms merely to make M0 pass.
Do not modify legacy project files.

## EXACT EXECUTION

1. Create/use `.venv` and install `requirements.txt` only if needed.
2. Run focused baseline:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

3. Set:

```powershell
$env:IMPLEMENTATION_PROFILE="m0"
$env:PROVIDER="ollama"
$env:LOCAL_LLM_MODEL="qwen3:4b"
```

4. Run:

```powershell
.\.venv\Scripts\python.exe scripts\check_local_llm.py
```

This must prove clean JSON-mode local inference. `app/providers/ollama.py` is expected to send `think=false` and structured-answer calls must use JSON format.

5. Run the real 12-case calibration exactly once initially:

```powershell
.\.venv\Scripts\python.exe scripts\run_m0_calibration.py --provider ollama
```

6. Inspect all 12 cases:
   - 9 evidence-present cases: expected evidence behavior and valid citation locator.
   - 3 missing-evidence cases: no fabricated citation.
   - record status, model, tokens, E2E latency, retrieval latency, RAM/VRAM where available.

7. Human-grade every case:
   - `manual_correctness = PASS/PARTIAL/FAIL`
   - `manual_faithfulness = PASS/PARTIAL/FAIL`
   - short reason for PARTIAL/FAIL.

Do not alter cases/config merely to improve scores.

8. Run the web app:

```powershell
.\START_M0_LOCAL.ps1
```

Manual smoke:
   - import source;
   - grounded question;
   - click citation and verify exact excerpt;
   - missing-evidence question;
   - inspect trace/metrics/source snapshot/config hash.

9. Restart from a fresh process and rerun at least two smoke cases to validate restore/reproducibility.

10. Generate the real-machine manifest:

```powershell
.\.venv\Scripts\python.exe scripts\create_m0_manifest.py
```

## TEST BUDGET

- Baseline suite once before changes.
- If code changes, run only the closest focused test first.
- Then run the full current repository suite once because this is the M0 gate.
- Do not rerun passing tests unless affected code changed afterward.
- Do not run M1/M2 experiment suites.

## FAILURE POLICY

If `qwen3:4b` is OOM, unstable, or operationally too slow:

```text
1. record the evidence;
2. do not silently change corpus/retrieval config;
3. only then test one smaller local fallback;
4. report the model comparison.
```

If a fix requires architecture redesign or M1/M2 code:

```text
STOP with SCOPE_EXPANSION_REQUIRED
```

If an unrelated test fails:

```text
REPORT ONLY unless it blocks M0 runtime directly.
```

## ACCEPTANCE

Return `M0_LOCAL_GATE_PASS` only if all are true:

```text
unit/integration tests PASS
real qwen3:4b local inference PASS
12/12 calibration runs completed
citation locator structurally valid for evidence cases
missing-evidence cases do not fabricate citations
hard context/token budget not bypassed
trace includes model/config/corpus snapshot/status
latency and RAM/VRAM measurements recorded
manual correctness/faithfulness review completed
source viewer smoke PASS
restart/restore smoke PASS
no P0/P1 M0 blocker remains
```

Otherwise return exactly:

```text
M0_LOCAL_GATE_PARTIAL
```

or:

```text
M0_LOCAL_GATE_FAIL
```

## OUTPUT FILES

Create/update:

```text
reports/M0_LOCAL_GATE_REPORT.md
reports/calibration/<real local calibration>.json
reports/calibration/<real local calibration>.csv
config/releases/m0_candidate_manifest.json
```

If code changed, also create:

```text
docs/M0_BLOCKER_FIXES.md
```

## COMMIT

If and only if the gate is PASS:

```text
commit the verified M0 changes/results on the current task branch
create an M0 verified checkpoint/tag only after the report is complete
```

Do not push.
Do not merge unrelated branches.

If PARTIAL/FAIL, commit only blocker fixes if they are independently verified; do not create an M0-DONE tag.

## REPORT <= 18 LINES

```text
DECISION:
BRANCH:
START_HEAD:
END_HEAD:
MODEL:
TESTS:
CALIBRATION:
CITATIONS:
MANUAL_CORRECTNESS:
MANUAL_FAITHFULNESS:
MEDIAN_E2E:
P95_E2E:
PEAK_RAM:
PEAK_VRAM:
BLOCKERS:
FILES_CHANGED:
COMMIT:
NEXT:
```

HARD STOP.
Do not continue to M1/M2.
