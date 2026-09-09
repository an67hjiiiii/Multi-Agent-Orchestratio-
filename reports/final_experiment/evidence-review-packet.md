# Evaluator-only evidence review packet

Status: DRAFT_FOR_HUMAN_REVIEW (never runtime input; never copied to prompts).
The excerpts below are copied from the frozen `data/m1-pilot-authorized-v1/sources.json` snapshot for semantic review only.

## src_c7f92b35e6b484c5_c0000
- source_name: `demo_api.md`
- index: `0`
- review_relevance: REST boundary: request validation, error responses, authorization requirements, and explicit dependency wording.
- canonical_text: # API and architecture demo evidence
The service exposes REST endpoints. API contracts should define request validation, error responses and authorization requirements. Architectural dependencies should be explicit when one task requires output produced by another task.

## src_1055b8f580d99531_c0000
- source_name: `demo_database.md`
- index: `0`
- review_relevance: Relational records: frequently used identifier filters, appropriate-index review, and consistency-sensitive transaction boundaries.
- canonical_text: # Database demo evidence
User records are stored in the relational database. Queries that filter by frequently used identifiers should be reviewed for appropriate indexes. Transaction boundaries are required for multi-step writes that must remain consistent.

## src_ecad6843b8fcb99b_c0000
- source_name: `demo_security.md`
- index: `0`
- review_relevance: Access control: bearer-token identity evidence, server-side permission checks, and the JWT/server-policy caveat.
- canonical_text: # Authentication and authorization demo evidence
The application uses bearer access tokens. Authentication verifies identity. Authorization checks whether the authenticated user has permission to perform an action. JWT claims must not be treated as a substitute for server-side authorization policy.
