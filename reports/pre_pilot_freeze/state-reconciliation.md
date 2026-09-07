# State reconciliation

Canonical state now promotes only evidenced fields: frozen qwen3:4b model,
frozen M1 source snapshot, verified hardware profile, local Ollama health,
approved development/validation pilot-subset benchmark and semantic gold, plus
experiment freeze ID `ce53402ae17731020c4e75330bc6b1f674f60c7e20087353008f3c1e08518e3a`.

This freeze updates only the committed pilot-runner/ledger wiring; model,
corpus, benchmark inputs, gold, metric schema, conditions, and hardware remain
unchanged. The ID is the SHA-256 of canonical JSON hash material.

M1 remains authorized for the human-approved development/validation pilot. The
15-case set is not a full empirical benchmark; M2 development ablations remain
conditional on the M1 development gate.
