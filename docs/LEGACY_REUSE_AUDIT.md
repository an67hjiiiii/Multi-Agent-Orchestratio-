# Legacy Reuse Audit — Clean Migration Decision

## Decision
The previous Adaptive Agent project is a **donor**, not the research base. The new repository must not inherit old research semantics.

## REUSE / PORT
- UI visual language and 3-pane chat/inspector concept.
- File ingestion ideas: normalization, chunk IDs, provenance.
- Conversation/run persistence patterns.
- Generic DAG validation/ready-node logic.
- Fake-provider testing concept.
- Trace/metrics presentation concept.

## REFACTOR
- RAG: retain text normalization/chunk/provenance ideas; replace retrieval and context-allocation research logic.
- Run metrics: retain generic counters; replace cost/adaptive-routing metrics with task/evidence/context metrics.
- Inspector: keep shell, replace old strategy terminology.

## REWRITE
- Research pipeline.
- Experiment runner and A/B/C/C-P/C-N/C-O conditions.
- Planning Retrieval P, Task Normalization N, Context Controller O.
- Local provider path.

## DROP FROM NEW RESEARCH BUILD
- DIRECT/PARALLEL/PLANNED as product/research semantics.
- Single/Fixed/Static/Adaptive strategy family.
- Old complexity classifier and adaptive escalation claims.
- Cloud provider selection in research execution.
- Dollar-cost optimization as a central metric.
- Old Pilot benchmark as evidence for the new research question.

## Safety boundary
Only `fake` and `ollama` providers exist in this clean build. No OpenAI/Gemini/Groq/OpenRouter adapter is imported or configured.
