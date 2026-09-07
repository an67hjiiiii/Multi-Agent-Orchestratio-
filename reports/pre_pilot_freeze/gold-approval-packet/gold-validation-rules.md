# Gold validation rules

Approved rows require unique non-empty obligation IDs; a case ID in the frozen
benchmark manifest; evidence IDs resolving in the frozen corpus manifest;
approved role/domain vocabulary; and human reviewer ID plus timestamp.
`relevant_evidence_ids` may be empty only for an explicit `NO_EVIDENCE` case
with `expected_missing_information` recorded. Evaluation tooling may read gold
only after generation. Runtime generation must not import this packet.
