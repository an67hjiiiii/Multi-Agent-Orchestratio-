# Pilot canonicalization policy

## Owner decision

This policy records the owner's decision for future, explicitly authorized
pilot reconciliation. It does not migrate, rewrite, classify, or invalidate
any existing raw attempt artifact.

Historical raw attempts remain raw evidence until an owner separately
authorizes a reconciliation operation against a named ledger and artifact set.

## Deterministic selection rule

For attempts with the same complete identity, select the earliest valid
terminal attempt as the canonical attempt. Later valid terminal attempts with
that identity remain `duplicate_attempt` records.

The identity must include at least:

- case ID;
- condition;
- immutable configuration identity/config hash;
- provider and model;
- corpus/source snapshot identity; and
- pilot manifest identity.

The rule is outcome-independent: terminal status, answer content, score,
latency, token usage, and any later review result must not influence which
attempt is selected.

If an identity field is absent, conflicts, or cannot be verified, or if the
ordering timestamp is absent, malformed, or ambiguous, leave the attempts
`UNRESOLVED`. Do not infer a canonical attempt and do not discard raw evidence.

## Scope boundary

Future pilot execution, resume execution, provider/model calls, and
canonicalization of the 23 historical raw attempts are not authorized by this
policy. The repository scope remains locked at P-lite under `AGENTS.md`.
