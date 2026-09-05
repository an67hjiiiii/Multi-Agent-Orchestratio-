# Local LLM setup

## Do you need to download an LLM now?
No for the clean S0 wiring build: `PROVIDER=fake` is the default and all pipeline/tests can run without a model.

Yes before validating the real product behavior: the research system must eventually run a local LLM. The repository is prepared for Ollama and defaults to `qwen3:4b` as a **calibration candidate**, not a frozen research choice.

## Recommended sequence
1. Run S0 with FakeProvider first.
2. Install Ollama on the Windows machine.
3. Pull one 4B-class candidate, e.g. `ollama pull qwen3:4b`.
4. Run `USE_LOCAL_OLLAMA.ps1`.
5. Measure JSON reliability, latency, RAM/VRAM and thermal behavior before freezing the model.

Do not download multiple models yet. The model choice is not frozen until calibration.
