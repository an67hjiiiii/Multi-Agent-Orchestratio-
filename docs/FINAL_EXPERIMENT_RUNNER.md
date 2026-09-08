# Final six-condition runner

`app.evaluation.final_experiment` and `scripts/run_final_experiment.py` provide
the reusable serial harness for `A`, `B`, `C`, `C-P`, `C-N`, and `C-O`.

The harness is plumbing only until the owner approves both the final dataset
and semantic gold. The default invocation is therefore blocked with
`PENDING_HUMAN_APPROVAL`:

```powershell
& "C:\Users\Viet Anh\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" scripts/run_final_experiment.py --dry-run
```

`--dry-run` prints a deterministic plan and never loads cases, creates a
pipeline, or calls a provider. A future launch must explicitly pass
`--dataset-status APPROVED --gold-status APPROVED`; no status is inferred from
the presence of a file.

Each request/condition/repeat has a stable `attempt_id` derived from the
experiment, case, condition, repeat, and immutable effective-config hash.
Generation is serial (`concurrency=1`) and has no automatic retry. A terminal
`COMPLETE`, `PARTIAL`, `NO_EVIDENCE`, or `FAILED` result is appended to
`canonical_attempt_ledger.jsonl` immediately. Resume skips canonical keys and
retains prior failures as evidence.

The runner accepts request-only cases. Gold-shaped fields are rejected, and no
gold loader is available to generation. `evaluate_after_inference()` first
loads the persisted report and verifies that every row is terminal; only then
does it call the supplied gold loader. Human grading remains `PENDING`.

This runner does not create or modify a final dataset/gold packet and does not
establish semantic or milestone evidence by itself. The focused tests use only
FakeProvider-style injected pipeline behavior and temporary files.
