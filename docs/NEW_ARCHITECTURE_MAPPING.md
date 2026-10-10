# New Architecture Mapping

```text
Request
  -> Planning Retrieval P (optional by condition)
  -> Task Decomposer
  -> Task Normalizer N (optional)
  -> Domain Registry / Assignment
  -> DAG validation + dependency order
  -> Task-specific Retrieval
  -> Context Controller O (optional)
  -> Domain Worker
  -> Structured Task Result
  -> Synthesizer
  -> Final Answer + Source IDs + Trace/Metrics
```

## Conditions
- A: Vanilla RAG.
- B: LLM decomposition + task RAG + workers, no P/N/O.
- C: P + N + O.
- C-P / C-N / C-O: controlled ablations.

## S0 implementation note
S0 intentionally uses lexical retrieval, conservative exact/near-exact task normalization, exact evidence dedup and a character-budget proxy. These are wiring implementations, not the final M2 algorithms or research results.
