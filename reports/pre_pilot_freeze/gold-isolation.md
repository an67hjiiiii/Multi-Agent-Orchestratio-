# Gold isolation guard

Decision: **PASS** for the current repository's static generation sources.

`verify_gold_isolation` inspects pipeline, decomposer, worker, synthesizer,
planning retrieval, and Ollama adapter for packet/gold markers. It does not
read gold values and returns violations deterministically. Focused tests prove
both current PASS and synthetic violation detection. Scope limit: this cannot
prove facts about future external data; gold remains evaluation-only after
generation.
