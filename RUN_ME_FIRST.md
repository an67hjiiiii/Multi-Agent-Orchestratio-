# RUN ME FIRST

## 1. Wiring test

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\START_WINDOWS.ps1
```

Open `http://127.0.0.1:8000`.

At profile M0 the UI should expose only condition **A**. Import a UTF-8 text/Markdown/code file, ask a grounded question, then click a citation ID to open the exact chunk.

## 2. Real M0 gate

Fake Provider only proves wiring. To validate the milestone with a real local model, follow:

`docs/CODEX_M0_LOCAL_GATE_PROMPT.md`

or run:

```powershell
.\RUN_M0_CALIBRATION_LOCAL.ps1
```

Do not mark M0 DONE until the target-laptop gate passes.
