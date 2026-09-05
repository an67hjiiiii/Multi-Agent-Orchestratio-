# M0 calibration runner

`scripts/run_m0_calibration.py` is the serial runner for the locked 12-case
M0 calibration set. It exercises condition `A` only and rebuilds the source
store from `datasets/domain/*.md` before each invocation.

## Scope and evidence boundary

- `datasets/calibration/m0_cases.json` is an input manifest, not a tuning
  target. The runner rejects a count, ID/order, evidence label, query, or
  expected-source mismatch.
- The runner always uses `IMPLEMENTATION_PROFILE=m0` and condition `A`.
- `--provider fake` is the quota-free wiring/test path. It does not establish
  local-model quality or promote M0.
- `--provider ollama` is reserved for the final target-laptop integration gate;
  this repository test does not call Ollama.
- Automated checks cover run status, citation locator structure, expected
  evidence behavior, expected source mapping, and M0 identity. They do not
  establish semantic correctness or faithfulness. Manual scores remain
  `UNSCORED` until a human reviews the answer and its evidence.

## Usage

From the repository root, run the deterministic wiring path with:

```powershell
python scripts/run_m0_calibration.py --provider fake
```

For the target laptop only, after the local Ollama preflight and with explicit
approval for the M0 gate:

```powershell
python scripts/run_m0_calibration.py --provider ollama
```

The runner accepts `--cases-path`, `--corpus-dir`, `--data-dir`, `--runs-dir`,
and `--output-dir` for isolated reproducibility checks. `--stamp` gives the
output files a stable filename, for example `--stamp 20260906T120000Z`.

Cases are executed sequentially, with no runner-level retry or condition
fallback. An unexpected case-level exception is represented as `FAILED` so the
report still has one row per case and does not silently omit an attempt.

## Outputs

Each invocation writes matching files under `reports/calibration/` (or the
selected output directory):

- `m0_calibration_<provider>_<stamp>.json` contains the report schema, dataset
  SHA-256, corpus snapshot, observed model/config/profile identifiers, stable
  case order, per-case answers/citations/metrics, and deterministic summaries.
- `m0_calibration_<provider>_<stamp>.csv` uses the fixed `REPORT_FIELDS` order
  from the runner so columns do not depend on provider output.

The report records runtime IDs and measurements such as run ID, latency, and
RSS; therefore a live report is not byte-identical across runs. Determinism
means the validated input, case order, row schema, aggregation rules, and
output naming can be reproduced and audited.
