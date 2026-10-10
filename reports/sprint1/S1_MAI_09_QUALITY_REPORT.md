# Sprint 1 quality report

## Scope and result

This report covers the approved 36 Sprint 1 tasks only. It records technical
contract and persistence checks; it does not claim live-model quality or
semantic correctness.

Verified code integration before this report: `cd03ff0c14ff679539c85c94af61d1e9dc1c43f7`.

## Test results

| Gate | Result | Evidence |
| --- | --- | --- |
| Backend Sprint 1 regression | PASS | 33 passed, 2 dependency deprecation warnings. Auth register/login/logout/session, source ownership, PDF upload, PostgreSQL schema, source store, pipeline, planning/dependency, decomposer contract, and execution contract tests. |
| Frontend tests | PASS | 4 passed, 0 failed. Session bootstrap and React/Vite entry wiring. |
| TypeScript and production build | PASS | `tsc -b` passed; Vite transformed 39 modules and emitted JS/CSS bundles. |
| PostgreSQL migration | PASS | Clean temporary `postgres:16` database upgraded to Alembic head `20261010_02`; server reported 16.15. |
| PostgreSQL ORM persistence | PASS | User, source, chunk, conversation, message, and run rows survived session close and engine reconnect. Cross-owner run/conversation FK mismatch was rejected. |
| Whitespace check | PASS | `git diff --check` passed for task commits and this report. |

The PostgreSQL evidence covers the S1 schema/ORM foundation. It does not claim
that product runtime stores are PostgreSQL-backed: the current app still uses
file-backed AuthStore, SourceStore, and RunStore, and the schema has no
session table. This boundary is recorded rather than silently counted as
runtime database migration.

## Task verification summary

The catalog's Jira status column was not used as code-reality status.

| Owner | Tasks with code/test commits | Verified without a code change |
| --- | --- | --- |
| ANH | S1-ANH-01, 02, 03, 04, 05, 07 | S1-ANH-06 |
| HAI | S1-HAI-01, 02, 03, 04, 05, 06, 07 | — |
| MAI | S1-MAI-09 | S1-MAI-01 through 08 |
| CHUNG | S1-CHUNG-02, 03, 05, 06 | S1-CHUNG-01, 04 |
| BẢO | S1-BẢO-05, 06, 07 | S1-BẢO-01 through 04 |

`VERIFIED_NO_CODE_CHANGE` means an existing Sprint 1 contract was exercised
by the focused regression; it does not create an empty task commit.

## Known issues and limits

- FastAPI/Starlette test client emits two upstream deprecation warnings.
- Product runtime persistence remains local-file based; PostgreSQL is currently
  a schema/ORM foundation only.
- No Ollama/model run or empirical-quality claim is included in Sprint 1 QA.
