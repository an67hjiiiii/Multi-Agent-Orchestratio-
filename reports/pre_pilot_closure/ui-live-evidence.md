# Local HTTP and UI evidence

The normal local FastAPI service ran at `127.0.0.1:8010` with profile `m1` and
provider `ollama`; server logs are retained beside this report. Health returned
allowed conditions `[A, B, C]`, default provider `ollama`, and a local corpus
snapshot ID.

| Path | Live run | Result |
| --- | --- | --- |
| HTTP A | `runs/run_79761de34b7f.json` | COMPLETE; vanilla retrieval events only |
| HTTP B | `runs/run_f5a2744f0f5e.json` | COMPLETE; decomposition and task retrieval, no P/N/O events |
| HTTP C | `runs/run_69ff518e3304.json` | COMPLETE; planning retrieval → decomposition → normalization → task retrieval → overlap summary |
| Browser UI C | `runs/run_e7b4d34303f5.json` | COMPLETE; UI selected `Condition=C`, `Provider=Local Ollama`, rendered two task answers and locator `[src_ecad6843b8fcb99b_c0000]` |

The browser accessibility tree is the UI evidence: it showed the rendered answer
and locator after submission. The raw run records are durable runtime evidence.
No remote provider was called.
