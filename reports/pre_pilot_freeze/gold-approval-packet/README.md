# Human gold approval packet

Gold is required for Evidence Recall@K, Role Assignment Accuracy, Task
Coverage, SufficientPass, and faithfulness/relevance review. The packet
contains request inputs and blank review fields only. Humans/teachers must
set `reviewer_status=APPROVED`; Codex/Terra must not do so. Gold files must not
be imported by generation prompts, retrieval, workers, synthesis, or runtime.
