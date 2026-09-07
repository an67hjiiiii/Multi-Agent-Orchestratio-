# Gold validation rules

Approved rows require unique non-empty obligation IDs; a case ID in the frozen
benchmark manifest; evidence IDs resolving in the frozen corpus manifest;
approved role/domain vocabulary; no required-field gaps; and human reviewer ID
plus timestamp. Evaluation tooling may read gold only after generation. Runtime
generation must not import this packet.
