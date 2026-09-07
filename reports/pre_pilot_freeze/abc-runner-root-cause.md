# A/B/C runner root cause

EXPECTED: `run_m1_pilot` iterates case → condition → repeat, atomically appends after each terminal run, advances to the next condition, and releases the single-writer lock in `finally`.

ACTUAL: the foreground Codex observer returned after showing only A. The same process continued outside that observation window: the immutable ledger later contained terminal B and C records. `m1-freeze-abc-final-v1` spans 69.579 s, while the observer returned at roughly 34 s. A separate 40 s non-M1 control also returned after about 11 s without its completion marker.

FIRST_DIVERGENCE: Codex/tool observation ended before the child command ended, after A was flushed and before B/C output was delivered.

ROOT_CAUSE: CODEX/HARNESS EXECUTION lifetime/observation timeout. It was not a runner loop, checkpoint, lock, Ollama, or A/B/C pipeline defect.

FIX_REQUIRED: NO production fix. Use a durable background process with file stdout/stderr/PID plus process/result polling for future long local runs.
