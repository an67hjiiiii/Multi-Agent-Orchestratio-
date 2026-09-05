# Development workflow

This document describes the repeatable local workflow for the foundation
repository. It does not change the milestone gates in the research plan.

## Prerequisites

- Python 3.13 for the supported CI baseline.
- A project virtual environment with `requirements.txt` installed.
- Ollama and the selected local model only when exercising real local
  inference. CI and ordinary wiring tests use `PROVIDER=fake`.

Create or activate the environment using the normal Windows project setup, then
run the focused checks:

```powershell
python -m compileall -q app scripts
python -m pytest -q
```

The equivalent CI command is `python -m pytest -q` with
`IMPLEMENTATION_PROFILE=m0` and `PROVIDER=fake`. No CI job starts Ollama,
contacts a hosted model, deploys an application, or reads inference secrets.

## Change discipline

1. Confirm the worktree, branch, and current HEAD before editing.
2. Keep one active writer per worktree and limit changes to the task ownership.
3. Prefer a focused test or documentation check before the broader backend
   test command.
4. Keep runtime data, `.env`, credentials, model files, and generated runs out
   of commits. Secrets must not appear in source, logs, traces, screenshots, or
   CI configuration.
5. Record limitations honestly: Fake/static/preflight evidence is wiring or
   non-semantic evidence, not proof of local-model quality or research results.

The static application under `app/static/` is part of the current FastAPI
package. If a separate `frontend/package.json` is introduced, CI automatically
runs its dependency install, build, and test scripts; otherwise the frontend job
is skipped.

## Profiles and gates

Use the narrowest profile that matches the work:

| Work | Profile/condition | Evidence boundary |
| --- | --- | --- |
| M0 wiring and tests | `m0`, A, Fake provider | Automated wiring only |
| Target-machine M0 gate | `m0`, A, local Ollama | Required for M0 DONE |
| M1 development | `m1`, A/B/C | Must include a real, scored pilot before M1 DONE |
| M2 evaluation | `m2`, six conditions | Requires frozen references, main evaluation, grading, statistics, and reconciliation |
| Future engineering experiments | `dev` | Never promote `dev` output as milestone evidence |

The current default model name `qwen3:4b` is a candidate configuration, not a
frozen research model. Freeze it only after the bounded target-laptop
calibration and review, then record the exact model tag/digest and runtime
manifest.

## Pull request checklist

- [ ] Scope and ownership are limited to the requested files.
- [ ] Backend compile and tests pass, or the failure is reported with its
  boundary and cause.
- [ ] New conditions/flags preserve schema, budget, citation, and failure
  guards.
- [ ] Model, corpus, config, and code identifiers are captured where a run or
  evaluation is affected.
- [ ] No cloud inference secret, runtime data, generated output, or deployment
  step was added.
- [ ] Claims distinguish `CANDIDATE`, `CHƯA XÁC MINH`, and verified evidence.

## Milestone handoff

Before handing off a milestone, provide the commit/reference, effective config
and hash, model/corpus/index manifest, case IDs and results, trace/metrics,
known limitations, start/restore commands, and reviewer status. Do not create a
release tag merely because code exists. Keep the previous LKG available until
the new checkpoint has passed its gate and restore smoke.
