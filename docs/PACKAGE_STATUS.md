# Package Status

Status: **REPO_READY / M0 CODE CANDIDATE**

Prepared for a brand-new Git repository on the target Windows laptop.

Verified in the packaging environment:

```text
compileall: PASS
pytest: 9 passed
Ollama provider contract: think=false + stream=false + JSON mode for structured answerers
Git bootstrap script: included
Worktree helper: included
Codex Luna M0 gate prompt: included
```

Not yet verified in this package environment:

```text
target-laptop 12-case Ollama calibration
manual grading
browser/source-viewer smoke on target laptop
restart/restore smoke
real-machine M0 release manifest
```

Therefore M0 is **not DONE** until the target-laptop gate passes.
