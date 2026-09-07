# Lock recovery

The earlier path was `reports/m1_pilot/m1-freeze-metric-smoke-v1/.pilot.lock`.
At recovery inspection no lock file and no Python pilot process existed; only
the local Ollama service was alive. Therefore no lock was deleted. The earlier
lock error was transient/orphaned outside observable repository code, and the
runner's `finally` cleanup remains covered by its focused lock test. A new
namespace is required for the bounded A/B/C smoke.
