# Clean Migration Plan

1. Freeze the old project; do not modify it.
2. Use this repository as the new source of truth for implementation.
3. S0: make A/B/C and all ablation flags run with FakeProvider.
4. Load the three demo domain documents and validate trace in the UI.
5. Install/verify a local Ollama model and rerun the same 3–5 development cases.
6. Only after S0 succeeds, implement M0/M1 quality work: corpus versioning, better retrieval, structured validation, calibrated P-lite/O-lite.
7. Do not import old orchestrator or pilot modules into this repository.
