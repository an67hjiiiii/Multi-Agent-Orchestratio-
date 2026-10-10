# Sprint 1 quality report

## Scope and result

This report covers the approved 36 Sprint 1 tasks only. It records technical
contract and persistence checks; it does not claim live-model quality or
semantic correctness.

Initial Sprint 1 snapshot: `a00d655c243cff49de539c201b613aa88237f610`.
This report is updated by the PostgreSQL-authoritative runtime correction
mapped to S1-HAI-05, S1-HAI-06, and S1-HAI-07.

## Test results

| Gate | Result | Evidence |
| --- | --- | --- |
| Backend Sprint 1 regression | PASS | 41 passed, 1 skipped (dedicated live PostgreSQL gate), 2 dependency deprecation warnings. Auth/session, source ownership, PDF upload, PostgreSQL stores, source store, pipeline, planning/dependency, decomposer contract, execution contract, and budget tests. |
| Frontend tests | PASS | 4 passed, 0 failed. Session bootstrap and React/Vite entry wiring. |
| TypeScript and production build | PASS | `tsc -b` passed; Vite transformed 39 modules and emitted JS/CSS bundles. |
| PostgreSQL migration | PASS | Clean temporary `postgres:16` database upgraded to Alembic head `20261010_03`; server reported 16.15. |
| PostgreSQL live product persistence | PASS | HTTP register/login/chat wrote user/session/source/chunk/conversation/message/run rows. Cross-user source/chunk/conversation/run access returned 404; logout revoked the session. Rows survived engine reconnect and Docker container restart. |
| Whitespace check | PASS | `git diff --check` passed for the final correction diff. |

The product default is now PostgreSQL and requires an explicit PostgreSQL
`DATABASE_URL`; missing configuration fails closed. `APP_STORAGE_BACKEND=file`
is an explicit test/dev selection only. No existing JSON data was migrated.

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
- Existing JSON data is not automatically imported into PostgreSQL; operators
  must keep the old data directory as a backup during deployment.
- No Ollama/model run or empirical-quality claim is included in Sprint 1 QA.
