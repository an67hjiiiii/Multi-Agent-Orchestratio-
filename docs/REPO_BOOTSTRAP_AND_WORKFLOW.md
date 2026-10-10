# CAP1 — New Repo Bootstrap + Working Rules

This package is intentionally **not** shipped with a `.git` directory. Create the real repository on the target Windows laptop so Git metadata, paths, runtime evidence, and checkpoints belong to the real machine.

## Recommended location

Extract this folder to:

```text
D:\Local-Multi-Agent-RAG
```

Then open PowerShell in that folder:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\BOOTSTRAP_NEW_REPO.ps1
```

Expected checkpoint:

```text
main
checkpoint/m0-code-candidate
m0-code-candidate-pre-gate
```

The checkpoint is **not** M0 DONE. It is only the pre-gate code candidate.

## Model policy

- Default coding/local-integration worker: **GPT-5.6 Luna — Chuyên sâu**.
- Escalate to Terra only with a concrete architecture/root-cause blocker.
- Reserve Sol for research/architecture decision gates, not routine local integration.

## Parallel work policy

- One active writer/chat per worktree.
- One production file owner per wave.
- Parallelize only ownership-independent work.
- Integration is a separate task.
- Local/provider benchmark runs should be serial when they share the same Ollama/GPU runtime.

Create a worktree only when parallel work is actually needed:

```powershell
.\NEW_WORKTREE.ps1 -Branch "codex/m1-planning" -FolderName "cap1-wt-m1-planning" -Base "main"
```

## M0 next action

M0 is currently a **code candidate**, not a completed milestone. The target-laptop gate must use the real local model.

Already verified manually on the target laptop before this package was prepared:

```text
GPU: RTX 3050 Laptop, 4 GB dedicated VRAM
RAM: 16 GB class
Ollama: working
Model: qwen3:4b downloaded and runnable
/api/chat: working
think=false: working via API
format=json: working via API
```

Run Codex Luna with:

```text
docs/CODEX_M0_LOCAL_GATE_PROMPT.md
```

Do not start M1 until the gate returns `M0_LOCAL_GATE_PASS` or the remaining blocker is reviewed explicitly.
