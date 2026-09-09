# Final Dataset V2 — compact human review bundle

Status: HUMAN_APPROVED. Review is scenario-level (30 groups), not 120 independent approvals.
Owner: PROJECT_OWNER | Approved at: 2026-09-09 | Result: 30/30 scenario groups PASS
Dataset SHA-256: 553b7e4de97bb3063d5f8f22994f368021b12a1439d8e4ea3d94b33dcbcd08ac
Gold SHA-256: 558f96f77aeddbee3dd815fdb09ea8c5e30c59988ef902bd0498b0e60122ce8d
The request manifest and scenario gold remain evaluator-only and must not be passed to runtime generation.

## M1F-S01 — Token intake and caller context
- SCENARIO_ID: M1F-S01
- PRIMARY_ARCHETYPE: SIMPLE_SINGLE_OBLIGATION
- DOMAINS: security
- CANONICAL_SEMANTIC_INTENT: Assess what caller context a bearer token gives the service at request intake.
- VARIANTS:
  - V1: Assess what caller context a bearer token gives the service at request intake.
  - V2: For a token-bearing call, state the identity-related conclusion supported by the security note.
  - V3: Summarize the security obligation attached to receiving an access token.
  - V4: What can the service establish about the caller from the bearer-token evidence?
- EXPECTED_STATUS: COMPLETE
- EVIDENCE:
  - src_ecad6843b8fcb99b_c0000 | Access control: bearer-token identity evidence, server-side permission checks, and the JWT/server-policy caveat.
- EXPECTED_MISSING_INFORMATION: NONE
- DEPENDENCY_EXPECTATION: NOT_APPLICABLE
- NORMALIZATION_EXPECTATION: NOT_APPLICABLE
- OVERLAP_EXPECTATION: NOT_APPLICABLE
- NEAREST_DEV_CASE: M1-01, M1-02
- WHY_HELD_OUT: It asks for the intake conclusion and does not repeat the development definition question or collapse authorization into it.
- REVIEW_STATUS: HUMAN_APPROVED

## M1F-S02 — Access review after token parsing
- SCENARIO_ID: M1F-S02
- PRIMARY_ARCHETYPE: SIMPLE_SINGLE_OBLIGATION
- DOMAINS: security
- CANONICAL_SEMANTIC_INTENT: Review an access-control audit note for reliance on token claims and name the control that remains necessary.
- VARIANTS:
  - V1: Review an access-control audit note for reliance on token claims and name the control that remains necessary.
  - V2: When a service reads a JWT, identify the authority boundary the audit should check.
  - V3: State the security safeguard that prevents token claims from becoming the whole permission decision.
  - V4: Evaluate whether a signed claim alone closes the server's protected-action review.
- EXPECTED_STATUS: COMPLETE
- EVIDENCE:
  - src_ecad6843b8fcb99b_c0000 | Access control: bearer-token identity evidence, server-side permission checks, and the JWT/server-policy caveat.
- EXPECTED_MISSING_INFORMATION: NONE
- DEPENDENCY_EXPECTATION: NOT_APPLICABLE
- NORMALIZATION_EXPECTATION: NOT_APPLICABLE
- OVERLAP_EXPECTATION: NOT_APPLICABLE
- NEAREST_DEV_CASE: M1-02, M1-07
- WHY_HELD_OUT: The holdout is an audit/authority-boundary composition rather than a direct 'what does authorization check' prompt.
- REVIEW_STATUS: HUMAN_APPROVED

## M1F-S03 — REST validation checkpoint
- SCENARIO_ID: M1F-S03
- PRIMARY_ARCHETYPE: SIMPLE_SINGLE_OBLIGATION
- DOMAINS: api_architecture
- CANONICAL_SEMANTIC_INTENT: Identify the request-validation check that belongs at the REST contract boundary.
- VARIANTS:
  - V1: Identify the request-validation check that belongs at the REST contract boundary.
  - V2: For a REST endpoint review, state the single obligation for validating incoming requests.
  - V3: What input-validation responsibility is documented for this API contract?
  - V4: Summarize only the validation step required before REST service work proceeds.
- EXPECTED_STATUS: COMPLETE
- EVIDENCE:
  - src_c7f92b35e6b484c5_c0000 | REST boundary: request validation, error responses, authorization requirements, and explicit dependency wording.
- EXPECTED_MISSING_INFORMATION: NONE
- DEPENDENCY_EXPECTATION: NOT_APPLICABLE
- NORMALIZATION_EXPECTATION: NOT_APPLICABLE
- OVERLAP_EXPECTATION: NOT_APPLICABLE
- NEAREST_DEV_CASE: M1-05, M1-11
- WHY_HELD_OUT: It isolates the invalid-request checkpoint while using a review context, not the development list question about all contract fields.
- REVIEW_STATUS: HUMAN_APPROVED

## M1F-S04 — Record storage and access review
- SCENARIO_ID: M1F-S04
- PRIMARY_ARCHETYPE: SIMPLE_SINGLE_OBLIGATION
- DOMAINS: database
- CANONICAL_SEMANTIC_INTENT: For a user-record service, summarize the database access review triggered by a frequently used identifier filter.
- VARIANTS:
  - V1: For a user-record service, summarize the database access review triggered by a frequently used identifier filter.
  - V2: What database follow-up belongs after identifying a hot lookup field in the user-record store?
  - V3: Review the storage note and state the access-path check for repeated identifier searches.
  - V4: When a relational service repeatedly filters on one identifier, which database concern should be examined?
- EXPECTED_STATUS: COMPLETE
- EVIDENCE:
  - src_1055b8f580d99531_c0000 | Relational records: frequently used identifier filters, appropriate-index review, and consistency-sensitive transaction boundaries.
- EXPECTED_MISSING_INFORMATION: NONE
- DEPENDENCY_EXPECTATION: NOT_APPLICABLE
- NORMALIZATION_EXPECTATION: NOT_APPLICABLE
- OVERLAP_EXPECTATION: NOT_APPLICABLE
- NEAREST_DEV_CASE: M1-03
- WHY_HELD_OUT: It combines storage context with a follow-up review decision instead of paraphrasing the development query about which queries need indexes.
- REVIEW_STATUS: HUMAN_APPROVED

## M1F-S05 — Consistency invariant for a write
- SCENARIO_ID: M1F-S05
- PRIMARY_ARCHETYPE: SIMPLE_SINGLE_OBLIGATION
- DOMAINS: database
- CANONICAL_SEMANTIC_INTENT: State the database safeguard that keeps a consistency-sensitive multi-step write together.
- VARIANTS:
  - V1: State the database safeguard that keeps a consistency-sensitive multi-step write together.
  - V2: For a write with several dependent changes, identify the boundary required by the database evidence.
  - V3: What protects a multi-step update whose intermediate state must not escape?
  - V4: Summarize the consistency obligation for a sequence of relational writes.
- EXPECTED_STATUS: COMPLETE
- EVIDENCE:
  - src_1055b8f580d99531_c0000 | Relational records: frequently used identifier filters, appropriate-index review, and consistency-sensitive transaction boundaries.
- EXPECTED_MISSING_INFORMATION: NONE
- DEPENDENCY_EXPECTATION: NOT_APPLICABLE
- NORMALIZATION_EXPECTATION: NOT_APPLICABLE
- OVERLAP_EXPECTATION: NOT_APPLICABLE
- NEAREST_DEV_CASE: M1-04
- WHY_HELD_OUT: The holdout frames an invariant and a write sequence rather than asking the same direct timing question.
- REVIEW_STATUS: HUMAN_APPROVED

## M1F-S06 — Protected write across API, security, and database
- SCENARIO_ID: M1F-S06
- PRIMARY_ARCHETYPE: MULTI_OBLIGATION_CROSS_DOMAIN
- DOMAINS: security, api_architecture, database
- CANONICAL_SEMANTIC_INTENT: Review a protected REST write: establish caller identity, enforce action permission, validate the request, and keep the database changes consistent.
- VARIANTS:
  - V1: Review a protected REST write: establish caller identity, enforce action permission, validate the request, and keep the database changes consistent.
  - V2: For a token-bearing user-record update, assess identity, connect the API contract, decide server permission, and review the multi-step transaction obligation.
  - V3: For a token-bearing REST write, establish caller identity, make the server-side permission decision, validate the API request, and protect the consistency-sensitive multi-step database write with a transaction boundary.
  - V4: Before accepting a protected multi-step REST update, assess caller identity, decide server-side permission, validate the API request, and keep the database changes consistent with transaction boundaries.
- EXPECTED_STATUS: COMPLETE
- EVIDENCE:
  - src_ecad6843b8fcb99b_c0000 | Access control: bearer-token identity evidence, server-side permission checks, and the JWT/server-policy caveat.
  - src_c7f92b35e6b484c5_c0000 | REST boundary: request validation, error responses, authorization requirements, and explicit dependency wording.
  - src_1055b8f580d99531_c0000 | Relational records: frequently used identifier filters, appropriate-index review, and consistency-sensitive transaction boundaries.
- EXPECTED_MISSING_INFORMATION: NONE
- DEPENDENCY_EXPECTATION: The review has four obligations but no required output dependency beyond keeping them distinct.
- NORMALIZATION_EXPECTATION: NOT_APPLICABLE
- OVERLAP_EXPECTATION: NOT_APPLICABLE
- NEAREST_DEV_CASE: M1-06, M1-07, M1-14
- WHY_HELD_OUT: This is a new end-to-end protected-write composition spanning all three frozen domains, not a pair or trio copied from development.
- REVIEW_STATUS: HUMAN_APPROVED

## M1F-S07 — Identity, API failure, and permission boundary
- SCENARIO_ID: M1F-S07
- PRIMARY_ARCHETYPE: MULTI_OBLIGATION_CROSS_DOMAIN
- DOMAINS: security, api_architecture
- CANONICAL_SEMANTIC_INTENT: Prepare a review of a REST endpoint that must identify its caller, reject invalid input, report errors, and enforce permission.
- VARIANTS:
  - V1: Prepare a review of a REST endpoint that must identify its caller, reject invalid input, report errors, and enforce permission.
  - V2: Connect bearer-token identity, request validation, error responses, and authorization for one protected API surface.
  - V3: Which separate controls should be recorded when an API receives a token but the request may still be invalid or unauthorized?
  - V4: Map the security and API obligations for a protected endpoint with both malformed and forbidden requests.
- EXPECTED_STATUS: COMPLETE
- EVIDENCE:
  - src_ecad6843b8fcb99b_c0000 | Access control: bearer-token identity evidence, server-side permission checks, and the JWT/server-policy caveat.
  - src_c7f92b35e6b484c5_c0000 | REST boundary: request validation, error responses, authorization requirements, and explicit dependency wording.
- EXPECTED_MISSING_INFORMATION: NONE
- DEPENDENCY_EXPECTATION: The obligations are independent checks in one endpoint review; no task must consume another task's output.
- NORMALIZATION_EXPECTATION: NOT_APPLICABLE
- OVERLAP_EXPECTATION: NOT_APPLICABLE
- NEAREST_DEV_CASE: M1-07, M1-14
- WHY_HELD_OUT: It introduces malformed-request behavior alongside identity/permission, a new cross-domain structure rather than a development pair.
- REVIEW_STATUS: HUMAN_APPROVED

## M1F-S08 — Data model, query access, and API input
- SCENARIO_ID: M1F-S08
- PRIMARY_ARCHETYPE: MULTI_OBLIGATION_CROSS_DOMAIN
- DOMAINS: database, api_architecture
- CANONICAL_SEMANTIC_INTENT: Review a user-record endpoint for input validation, relational storage, and index suitability on its common identifier lookup.
- VARIANTS:
  - V1: Review a user-record endpoint for input validation, relational storage, and index suitability on its common identifier lookup.
  - V2: For an API that searches user records, combine the request contract with the database access-path review.
  - V3: List the API and persistence obligations for a frequently used identifier filter exposed through REST.
  - V4: Assess how a user-record search should be checked at both the contract boundary and the relational query boundary.
- EXPECTED_STATUS: COMPLETE
- EVIDENCE:
  - src_1055b8f580d99531_c0000 | Relational records: frequently used identifier filters, appropriate-index review, and consistency-sensitive transaction boundaries.
  - src_c7f92b35e6b484c5_c0000 | REST boundary: request validation, error responses, authorization requirements, and explicit dependency wording.
- EXPECTED_MISSING_INFORMATION: NONE
- DEPENDENCY_EXPECTATION: The obligations are parallel API/database checks; neither output is required to construct the other.
- NORMALIZATION_EXPECTATION: NOT_APPLICABLE
- OVERLAP_EXPECTATION: NOT_APPLICABLE
- NEAREST_DEV_CASE: M1-03, M1-05, M1-08
- WHY_HELD_OUT: It couples a search endpoint with input handling, a relationship not present in the development prompts.
- REVIEW_STATUS: HUMAN_APPROVED

## M1F-S09 — Authorized write with identity and transaction
- SCENARIO_ID: M1F-S09
- PRIMARY_ARCHETYPE: MULTI_OBLIGATION_CROSS_DOMAIN
- DOMAINS: security, database
- CANONICAL_SEMANTIC_INTENT: For a user-record write, review caller identity, server permission, and the consistency boundary around the database changes.
- VARIANTS:
  - V1: For a user-record write, review caller identity, server permission, and the consistency boundary around the database changes.
  - V2: For a token-bearing relational update, assess caller identity separately from the server-side permission decision, then review the transaction boundary for consistency.
  - V3: Audit a multi-step record change by assessing caller identity, deciding server-side permission, and reviewing the transaction/consistency boundary.
  - V4: Before a bearer-token request may perform a consistency-sensitive database write, assess caller identity, make the server permission decision, and review the transaction boundary.
- EXPECTED_STATUS: COMPLETE
- EVIDENCE:
  - src_ecad6843b8fcb99b_c0000 | Access control: bearer-token identity evidence, server-side permission checks, and the JWT/server-policy caveat.
  - src_1055b8f580d99531_c0000 | Relational records: frequently used identifier filters, appropriate-index review, and consistency-sensitive transaction boundaries.
- EXPECTED_MISSING_INFORMATION: NONE
- DEPENDENCY_EXPECTATION: The checks remain separate and parallel; the prompt does not require one result to be fed into another task.
- NORMALIZATION_EXPECTATION: NOT_APPLICABLE
- OVERLAP_EXPECTATION: NOT_APPLICABLE
- NEAREST_DEV_CASE: M1-06, M1-14
- WHY_HELD_OUT: The new unit of analysis is an authorized consistency-sensitive write, not the development request's loose list of requirements.
- REVIEW_STATUS: HUMAN_APPROVED

## M1F-S10 — Service review with three evidence surfaces
- SCENARIO_ID: M1F-S10
- PRIMARY_ARCHETYPE: MULTI_OBLIGATION_CROSS_DOMAIN
- DOMAINS: api_architecture, security, database
- CANONICAL_SEMANTIC_INTENT: Create a cross-domain review for a REST service that validates input, protects access with bearer evidence, and persists user records safely.
- VARIANTS:
  - V1: Create a cross-domain review for a REST service that validates input, protects access with bearer evidence, and persists user records safely.
  - V2: Summarize the contract, access-control, and relational-write concerns that belong in one service-readiness note.
  - V3: For a service handoff, identify API behavior, permission enforcement, and database consistency obligations without merging them.
  - V4: Review a user-facing endpoint from request acceptance through authorized, consistent persistence.
- EXPECTED_STATUS: COMPLETE
- EVIDENCE:
  - src_c7f92b35e6b484c5_c0000 | REST boundary: request validation, error responses, authorization requirements, and explicit dependency wording.
  - src_ecad6843b8fcb99b_c0000 | Access control: bearer-token identity evidence, server-side permission checks, and the JWT/server-policy caveat.
  - src_1055b8f580d99531_c0000 | Relational records: frequently used identifier filters, appropriate-index review, and consistency-sensitive transaction boundaries.
- EXPECTED_MISSING_INFORMATION: NONE
- DEPENDENCY_EXPECTATION: The four obligations are parallel service-readiness concerns; no dependency order is required.
- NORMALIZATION_EXPECTATION: NOT_APPLICABLE
- OVERLAP_EXPECTATION: NOT_APPLICABLE
- NEAREST_DEV_CASE: M1-05, M1-06, M1-14, M1-15
- WHY_HELD_OUT: It creates a service-readiness review around a lifecycle rather than reusing any one development wording or pair.
- REVIEW_STATUS: HUMAN_APPROVED

## M1F-S11 — Identity output feeds permission review
- SCENARIO_ID: M1F-S11
- PRIMARY_ARCHETYPE: DEPENDENCY_TASK_GRAPH
- DOMAINS: security
- CANONICAL_SEMANTIC_INTENT: Produce a two-step review: first record the caller identity established from the token, then use that result to assess permission for the requested action.
- VARIANTS:
  - V1: Produce a two-step review: first record the caller identity established from the token, then use that result to assess permission for the requested action.
  - V2: Build a task graph where identity evidence is the input to the server-side authorization decision.
  - V3: Explain what the first security task must return before the access-control task can be evaluated.
  - V4: Order the protected-action review so the permission task consumes a completed identity assessment.
- EXPECTED_STATUS: COMPLETE
- EVIDENCE:
  - src_ecad6843b8fcb99b_c0000 | Access control: bearer-token identity evidence, server-side permission checks, and the JWT/server-policy caveat.
- EXPECTED_MISSING_INFORMATION: NONE
- DEPENDENCY_EXPECTATION: Task 2 depends on Task 1's identity assessment; it must not run as an independent permission-only task.
- NORMALIZATION_EXPECTATION: NOT_APPLICABLE
- OVERLAP_EXPECTATION: NOT_APPLICABLE
- NEAREST_DEV_CASE: M1-09
- WHY_HELD_OUT: The required dependency is an explicit output contract (identity result consumed by permission), not merely the word 'first'.
- REVIEW_STATUS: HUMAN_APPROVED

## M1F-S12 — Storage decision feeds index review
- SCENARIO_ID: M1F-S12
- PRIMARY_ARCHETYPE: DEPENDENCY_TASK_GRAPH
- DOMAINS: database
- CANONICAL_SEMANTIC_INTENT: Create an ordered database analysis: determine the user-record storage context first, then use it to scope the frequently used identifier index review.
- VARIANTS:
  - V1: Create an ordered database analysis: determine the user-record storage context first, then use it to scope the frequently used identifier index review.
  - V2: The second task must receive the storage finding before evaluating the access path for repeated lookups; specify both tasks.
  - V3: Design a dependency chain from record-storage identification to an appropriate-index recommendation.
  - V4: What output from the storage task is required before the query-access task can be scoped?
- EXPECTED_STATUS: COMPLETE
- EVIDENCE:
  - src_1055b8f580d99531_c0000 | Relational records: frequently used identifier filters, appropriate-index review, and consistency-sensitive transaction boundaries.
- EXPECTED_MISSING_INFORMATION: NONE
- DEPENDENCY_EXPECTATION: The index-review task is scoped by Task 1's storage finding; it should not invent a different store or schema.
- NORMALIZATION_EXPECTATION: NOT_APPLICABLE
- OVERLAP_EXPECTATION: NOT_APPLICABLE
- NEAREST_DEV_CASE: M1-03, M1-08
- WHY_HELD_OUT: The dependency names a concrete storage finding that constrains the second task, unlike the development ordering prompt.
- REVIEW_STATUS: HUMAN_APPROVED

## M1F-S13 — Validation result feeds error contract
- SCENARIO_ID: M1F-S13
- PRIMARY_ARCHETYPE: DEPENDENCY_TASK_GRAPH
- DOMAINS: api_architecture
- CANONICAL_SEMANTIC_INTENT: Split the API review into validation and response tasks: the error-response task must consume the validation outcome.
- VARIANTS:
  - V1: Split the API review into validation and response tasks: the error-response task must consume the validation outcome.
  - V2: Specify the output of request validation before defining how the REST contract reports the rejected request.
  - V3: Build a two-node API task graph from input checking to an appropriate error response.
  - V4: Which finding must the contract review produce before the error-handling task can be completed?
- EXPECTED_STATUS: COMPLETE
- EVIDENCE:
  - src_c7f92b35e6b484c5_c0000 | REST boundary: request validation, error responses, authorization requirements, and explicit dependency wording.
- EXPECTED_MISSING_INFORMATION: NONE
- DEPENDENCY_EXPECTATION: The error-response task consumes the validation finding; it is not a parallel list of API fields.
- NORMALIZATION_EXPECTATION: NOT_APPLICABLE
- OVERLAP_EXPECTATION: NOT_APPLICABLE
- NEAREST_DEV_CASE: M1-05, M1-11
- WHY_HELD_OUT: It tests an output-to-input contract between validation and error handling, a relationship absent from the development cases.
- REVIEW_STATUS: HUMAN_APPROVED

## M1F-S14 — Protected write three-stage chain
- SCENARIO_ID: M1F-S14
- PRIMARY_ARCHETYPE: DEPENDENCY_TASK_GRAPH
- DOMAINS: security, database
- CANONICAL_SEMANTIC_INTENT: Construct three dependent tasks for a protected record write: establish identity, authorize the action, then place the allowed multi-step write inside a consistency boundary.
- VARIANTS:
  - V1: Construct three dependent tasks for a protected record write: establish identity, authorize the action, then place the allowed multi-step write inside a consistency boundary.
  - V2: Assess identity first, then authorize the action; only after that allow decision may the transaction task start. Show the complete chain.
  - V3: Define outputs for identity and authorization that gate the final database-consistency task.
  - V4: Order a token-bearing relational update by assessing identity, deciding permission, and then consuming that result in the transaction task.
- EXPECTED_STATUS: COMPLETE
- EVIDENCE:
  - src_ecad6843b8fcb99b_c0000 | Access control: bearer-token identity evidence, server-side permission checks, and the JWT/server-policy caveat.
  - src_1055b8f580d99531_c0000 | Relational records: frequently used identifier filters, appropriate-index review, and consistency-sensitive transaction boundaries.
- EXPECTED_MISSING_INFORMATION: NONE
- DEPENDENCY_EXPECTATION: Task 2 depends on identity; Task 3 depends on an allowed authorization result and then applies the database consistency rule.
- NORMALIZATION_EXPECTATION: NOT_APPLICABLE
- OVERLAP_EXPECTATION: NOT_APPLICABLE
- NEAREST_DEV_CASE: M1-09, M1-14
- WHY_HELD_OUT: It adds a three-stage security-to-database output chain; the development case has no explicit gate into the write task.
- REVIEW_STATUS: HUMAN_APPROVED

## M1F-S15 — API authorization contract gates persistence
- SCENARIO_ID: M1F-S15
- PRIMARY_ARCHETYPE: DEPENDENCY_TASK_GRAPH
- DOMAINS: api_architecture, security, database
- CANONICAL_SEMANTIC_INTENT: First extract the endpoint's authorization requirement from the API contract, then use that requirement to scope the protected transaction-write review.
- VARIANTS:
  - V1: First extract the endpoint's authorization requirement from the API contract, then use that requirement to scope the protected transaction-write review.
  - V2: Make the database-consistency task depend on a completed API permission-contract finding.
  - V3: Trace the dependency from REST authorization wording to the transaction boundary for the resulting user-record write.
  - V4: What contract output must be available before a worker can assess the persistence boundary of an authorized request?
- EXPECTED_STATUS: COMPLETE
- EVIDENCE:
  - src_c7f92b35e6b484c5_c0000 | REST boundary: request validation, error responses, authorization requirements, and explicit dependency wording.
  - src_ecad6843b8fcb99b_c0000 | Access control: bearer-token identity evidence, server-side permission checks, and the JWT/server-policy caveat.
  - src_1055b8f580d99531_c0000 | Relational records: frequently used identifier filters, appropriate-index review, and consistency-sensitive transaction boundaries.
- EXPECTED_MISSING_INFORMATION: NONE
- DEPENDENCY_EXPECTATION: The persistence task is scoped by the authorization-contract output; it must not invent an unrelated write.
- NORMALIZATION_EXPECTATION: NOT_APPLICABLE
- OVERLAP_EXPECTATION: NOT_APPLICABLE
- NEAREST_DEV_CASE: M1-07, M1-14
- WHY_HELD_OUT: The dependency crosses API contract and database persistence with an explicit consumed artifact, not a simple multi-obligation list.
- REVIEW_STATUS: HUMAN_APPROVED

## M1F-S16 — Repeated identity obligation
- SCENARIO_ID: M1F-S16
- PRIMARY_ARCHETYPE: DUPLICATE_OVERLAPPING_OBLIGATION_N
- DOMAINS: security
- CANONICAL_SEMANTIC_INTENT: Normalize this review request: establish caller identity from the bearer token, and also verify the caller identity from the access token before proceeding.
- VARIANTS:
  - V1: Normalize this review request: establish caller identity from the bearer token, and also verify the caller identity from the access token before proceeding.
  - V2: The task list repeats the same identity-establishment obligation in token-intake and access-token language; produce the conservative normalized list.
  - V3: Collapse only the duplicate identity check in this request while preserving any genuinely different security work.
  - V4: Identify whether the two token identity clauses are one obligation or two, and return the normalized task set.
- EXPECTED_STATUS: COMPLETE
- EVIDENCE:
  - src_ecad6843b8fcb99b_c0000 | Access control: bearer-token identity evidence, server-side permission checks, and the JWT/server-policy caveat.
- EXPECTED_MISSING_INFORMATION: NONE
- DEPENDENCY_EXPECTATION: No dependency is required; the duplicate identity clauses can be compared independently.
- NORMALIZATION_EXPECTATION: MERGE the two exact canonical identity-establishment obligations; KEEP any distinct authorization obligation separate.
- OVERLAP_EXPECTATION: NOT_APPLICABLE
- NEAREST_DEV_CASE: M1-10
- WHY_HELD_OUT: The repeated obligation is embedded in a normalization decision and uses no development wording about repeating evidence.
- REVIEW_STATUS: HUMAN_APPROVED

## M1F-S17 — Repeated request-validation obligation
- SCENARIO_ID: M1F-S17
- PRIMARY_ARCHETYPE: DUPLICATE_OVERLAPPING_OBLIGATION_N
- DOMAINS: api_architecture
- CANONICAL_SEMANTIC_INTENT: Normalize the endpoint plan: check request validation for malformed input, then check the API request-validation requirement again under input screening.
- VARIANTS:
  - V1: Normalize the endpoint plan: check request validation for malformed input, then check the API request-validation requirement again under input screening.
  - V2: Two planned tasks both ask for the contract's request-validation obligation; return one canonical validation task.
  - V3: Detect the true duplicate between input-shape validation and request validation, while retaining error reporting as separate if present.
  - V4: Should the two validation clauses create one task or two? Apply the conservative normalization rule and explain the result.
- EXPECTED_STATUS: COMPLETE
- EVIDENCE:
  - src_c7f92b35e6b484c5_c0000 | REST boundary: request validation, error responses, authorization requirements, and explicit dependency wording.
- EXPECTED_MISSING_INFORMATION: NONE
- DEPENDENCY_EXPECTATION: The two validation tasks are peers; no dependency edge is needed for the merge decision.
- NORMALIZATION_EXPECTATION: MERGE only the duplicate request-validation obligations; KEEP error-response work separate because it is a distinct API obligation.
- OVERLAP_EXPECTATION: NOT_APPLICABLE
- NEAREST_DEV_CASE: M1-05, M1-11
- WHY_HELD_OUT: It explicitly tests duplicate validation wording and asks for a normalization decision, not an answer listing API fields.
- REVIEW_STATUS: HUMAN_APPROVED

## M1F-S18 — Repeated transaction-boundary obligation
- SCENARIO_ID: M1F-S18
- PRIMARY_ARCHETYPE: DUPLICATE_OVERLAPPING_OBLIGATION_N
- DOMAINS: database
- CANONICAL_SEMANTIC_INTENT: Normalize a write plan containing both 'keep the multi-step update consistent with a transaction boundary' and 'wrap the same multi-step update in a consistency transaction'.
- VARIANTS:
  - V1: Normalize a write plan containing both 'keep the multi-step update consistent with a transaction boundary' and 'wrap the same multi-step update in a consistency transaction'.
  - V2: The database plan states the transaction-boundary requirement twice with different wording; return the canonical task set.
  - V3: Decide whether atomic multi-step-write protection and a transaction boundary are duplicate obligations in this request.
  - V4: Remove only the redundant consistency-boundary task from the proposed relational write plan.
- EXPECTED_STATUS: COMPLETE
- EVIDENCE:
  - src_1055b8f580d99531_c0000 | Relational records: frequently used identifier filters, appropriate-index review, and consistency-sensitive transaction boundaries.
- EXPECTED_MISSING_INFORMATION: NONE
- DEPENDENCY_EXPECTATION: The duplicate clauses concern one write protection and have no required ordering dependency.
- NORMALIZATION_EXPECTATION: MERGE the repeated transaction-boundary obligation; KEEP query/index review separate because it addresses a different database concern.
- OVERLAP_EXPECTATION: NOT_APPLICABLE
- NEAREST_DEV_CASE: M1-04
- WHY_HELD_OUT: The holdout asks the normalizer to distinguish a duplicate consistency clause from a separate access-path concern.
- REVIEW_STATUS: HUMAN_APPROVED

## M1F-S19 — Repeated permission-decision obligation
- SCENARIO_ID: M1F-S19
- PRIMARY_ARCHETYPE: DUPLICATE_OVERLAPPING_OBLIGATION_N
- DOMAINS: security
- CANONICAL_SEMANTIC_INTENT: Normalize the access plan: decide whether the user may perform the action, and enforce the server permission decision for that same action.
- VARIANTS:
  - V1: Normalize the access plan: decide whether the user may perform the action, and enforce the server permission decision for that same action.
  - V2: The proposed security tasks repeat one authorization decision under 'permission check' and 'server enforcement'; produce one canonical obligation.
  - V3: Merge the duplicate action-permission review without collapsing identity verification into it.
  - V4: Return a conservative task list for two clauses that both require the server to decide access to one protected action.
- EXPECTED_STATUS: COMPLETE
- EVIDENCE:
  - src_ecad6843b8fcb99b_c0000 | Access control: bearer-token identity evidence, server-side permission checks, and the JWT/server-policy caveat.
- EXPECTED_MISSING_INFORMATION: NONE
- DEPENDENCY_EXPECTATION: The duplicate authorization clauses are independent comparison candidates; identity is not a dependency of the merge itself.
- NORMALIZATION_EXPECTATION: MERGE the duplicate server-side permission obligations; KEEP authentication/identity separate.
- OVERLAP_EXPECTATION: NOT_APPLICABLE
- NEAREST_DEV_CASE: M1-02, M1-07
- WHY_HELD_OUT: It tests canonical duplicate detection inside an access-plan request rather than asking the direct authorization definition.
- REVIEW_STATUS: HUMAN_APPROVED

## M1F-S20 — Duplicate API authorization inside a mixed plan
- SCENARIO_ID: M1F-S20
- PRIMARY_ARCHETYPE: DUPLICATE_OVERLAPPING_OBLIGATION_N
- DOMAINS: api_architecture, security, database
- CANONICAL_SEMANTIC_INTENT: Review a mixed service plan by establishing caller identity, confirming whether the caller may perform the requested action, verifying on the server that the user is permitted to carry it out, and checking the transaction boundary for the consistency-sensitive write.
- VARIANTS:
  - V1: Review a mixed service plan by establishing caller identity, confirming whether the caller may perform the requested action, verifying on the server that the user is permitted to carry it out, and checking the transaction boundary for the consistency-sensitive write.
  - V2: For a protected record operation, assess caller identity, decide whether the caller may perform the operation, verify that server-side policy permits that operation, and review the transaction boundary that preserves consistency.
  - V3: Assess a user-record service request: establish who is calling, determine whether the action is permitted, confirm server enforcement of that permission, and place the multi-step write within a transaction boundary.
  - V4: Review an identity-bearing write by recording caller identity, deciding whether the requested action is allowed by server policy, verifying that permission is enforced for the operation, and checking transaction boundaries for consistent updates.
- EXPECTED_STATUS: COMPLETE
- EVIDENCE:
  - src_c7f92b35e6b484c5_c0000 | REST boundary: request validation, error responses, authorization requirements, and explicit dependency wording.
  - src_ecad6843b8fcb99b_c0000 | Access control: bearer-token identity evidence, server-side permission checks, and the JWT/server-policy caveat.
  - src_1055b8f580d99531_c0000 | Relational records: frequently used identifier filters, appropriate-index review, and consistency-sensitive transaction boundaries.
- EXPECTED_MISSING_INFORMATION: NONE
- DEPENDENCY_EXPECTATION: The mixed plan has separate identity and transaction tasks; only the two canonical authorization duplicates are merge candidates.
- NORMALIZATION_EXPECTATION: MERGE the repeated authorization requirement; KEEP identity and transaction-boundary obligations separate, then remap dependencies without cycles.
- OVERLAP_EXPECTATION: NOT_APPLICABLE
- NEAREST_DEV_CASE: M1-07, M1-14
- WHY_HELD_OUT: This is a cross-domain normalization case with one true duplicate and two protected distinct obligations, not a paraphrase of either development case.
- REVIEW_STATUS: HUMAN_APPROVED

## M1F-S21 — Shared security evidence for two tasks
- SCENARIO_ID: M1F-S21
- PRIMARY_ARCHETYPE: SHARED_OVERLAPPING_EVIDENCE_O
- DOMAINS: security
- CANONICAL_SEMANTIC_INTENT: Retrieve context separately for two tasks: assess caller identity and assess permission for the requested action; report where the same security evidence is legitimately shared.
- VARIANTS:
  - V1: Retrieve context separately for two tasks: assess caller identity and assess permission for the requested action; report where the same security evidence is legitimately shared.
  - V2: Plan an identity task and an authorization task for one protected request without deleting the shared security source from either context.
  - V3: Show per-task evidence allocation for identity verification and server permission review when both need the security note.
  - V4: Which evidence may be reused by the two security workers, and what unnecessary duplicate context should the allocator flag?
- EXPECTED_STATUS: COMPLETE
- EVIDENCE:
  - src_ecad6843b8fcb99b_c0000 | Access control: bearer-token identity evidence, server-side permission checks, and the JWT/server-policy caveat.
- EXPECTED_MISSING_INFORMATION: NONE
- DEPENDENCY_EXPECTATION: The two tasks are independent; shared evidence is allowed because both obligations are grounded in the same security chunk.
- NORMALIZATION_EXPECTATION: NOT_APPLICABLE
- OVERLAP_EXPECTATION: KEEP shared evidence src_ecad6843b8fcb99b_c0000 for both identity and authorization; flag only repeated irrelevant context, and never drop evidence required by either task.
- NEAREST_DEV_CASE: M1-10
- WHY_HELD_OUT: It tests per-task overlap allocation and reuse accounting, not repeated-evidence wording in a decomposition request.
- REVIEW_STATUS: HUMAN_APPROVED

## M1F-S22 — Shared database evidence across storage and access tasks
- SCENARIO_ID: M1F-S22
- PRIMARY_ARCHETYPE: SHARED_OVERLAPPING_EVIDENCE_O
- DOMAINS: database
- CANONICAL_SEMANTIC_INTENT: Allocate context for a storage task and a query-access task that both need the database note to interpret user records and identifier filters.
- VARIANTS:
  - V1: Allocate context for a storage task and a query-access task that both need the database note to interpret user records and identifier filters.
  - V2: Retrieve separately for relational storage review and index suitability review, preserving the common database evidence where it is relevant.
  - V3: Show which database chunk is shared by the record-storage and repeated-lookup workers and which extra context, if any, can be dropped.
  - V4: Compare two task contexts for a user-record search without globally removing the evidence that grounds both tasks.
- EXPECTED_STATUS: COMPLETE
- EVIDENCE:
  - src_1055b8f580d99531_c0000 | Relational records: frequently used identifier filters, appropriate-index review, and consistency-sensitive transaction boundaries.
- EXPECTED_MISSING_INFORMATION: NONE
- DEPENDENCY_EXPECTATION: The storage and access tasks are parallel and each needs the same database evidence for a different conclusion.
- NORMALIZATION_EXPECTATION: NOT_APPLICABLE
- OVERLAP_EXPECTATION: KEEP shared evidence src_1055b8f580d99531_c0000 for both tasks; report unnecessary repetition separately rather than globally deduplicating it.
- NEAREST_DEV_CASE: M1-03, M1-08
- WHY_HELD_OUT: It changes the unit from a single index question to two per-task contexts with legitimate shared grounding.
- REVIEW_STATUS: HUMAN_APPROVED

## M1F-S23 — Shared API evidence for validation and errors
- SCENARIO_ID: M1F-S23
- PRIMARY_ARCHETYPE: SHARED_OVERLAPPING_EVIDENCE_O
- DOMAINS: api_architecture
- CANONICAL_SEMANTIC_INTENT: Allocate context to separate validation and error-response tasks for one REST contract, and preserve the API evidence both tasks require.
- VARIANTS:
  - V1: Allocate context to separate validation and error-response tasks for one REST contract, and preserve the API evidence both tasks require.
  - V2: Show the overlap summary when request checking and failure reporting retrieve the same API contract chunk.
  - V3: Which source can both API workers reuse while still recording distinct selected evidence per task?
  - V4: Compare task-specific contexts for malformed-input handling and error responses without treating shared API evidence as waste by default.
- EXPECTED_STATUS: COMPLETE
- EVIDENCE:
  - src_c7f92b35e6b484c5_c0000 | REST boundary: request validation, error responses, authorization requirements, and explicit dependency wording.
- EXPECTED_MISSING_INFORMATION: NONE
- DEPENDENCY_EXPECTATION: Validation and error-response tasks are separate but grounded by one API contract chunk.
- NORMALIZATION_EXPECTATION: NOT_APPLICABLE
- OVERLAP_EXPECTATION: KEEP shared evidence src_c7f92b35e6b484c5_c0000 for both tasks; do not drop it merely because it appears twice.
- NEAREST_DEV_CASE: M1-11
- WHY_HELD_OUT: It requires O's per-task overlap trace and shared-evidence retention rather than the development request's shared-evidence observation.
- REVIEW_STATUS: HUMAN_APPROVED

## M1F-S24 — Shared security/API context for a protected endpoint
- SCENARIO_ID: M1F-S24
- PRIMARY_ARCHETYPE: SHARED_OVERLAPPING_EVIDENCE_O
- DOMAINS: security, api_architecture
- CANONICAL_SEMANTIC_INTENT: Review a protected REST endpoint by assessing its authorization contract and server permission requirement, then assessing request validation and error behavior.
- VARIANTS:
  - V1: Review a protected REST endpoint: assess its authorization contract and server permission requirement, then assess request validation and error behavior.
  - V2: For one protected endpoint, evaluate how the server decides whether a caller may act and how the endpoint validates requests and reports errors.
  - V3: Audit a REST service for access control, including the server permission requirement, alongside input validation and error responses.
  - V4: Summarize the authorization and request-handling controls needed for a protected REST endpoint, covering server permission, validation, and error behavior.
- EXPECTED_STATUS: COMPLETE
- EVIDENCE:
  - src_ecad6843b8fcb99b_c0000 | Access control: bearer-token identity evidence, server-side permission checks, and the JWT/server-policy caveat.
  - src_c7f92b35e6b484c5_c0000 | REST boundary: request validation, error responses, authorization requirements, and explicit dependency wording.
- EXPECTED_MISSING_INFORMATION: NONE
- DEPENDENCY_EXPECTATION: The two workers address different obligations; shared endpoint evidence is legitimate, not a reason to merge tasks.
- NORMALIZATION_EXPECTATION: NOT_APPLICABLE
- OVERLAP_EXPECTATION: KEEP src_c7f92b35e6b484c5_c0000 as legitimate shared API evidence for both tasks; keep src_ecad6843b8fcb99b_c0000 specific to Task A and do not force it into Task B.
- NEAREST_DEV_CASE: M1-07, M1-11
- WHY_HELD_OUT: It creates a protected-endpoint overlap allocation across two source domains, a new task/evidence shape.
- REVIEW_STATUS: HUMAN_APPROVED

## M1F-S25 — Shared evidence in an authorized record workflow
- SCENARIO_ID: M1F-S25
- PRIMARY_ARCHETYPE: SHARED_OVERLAPPING_EVIDENCE_O
- DOMAINS: security, database
- CANONICAL_SEMANTIC_INTENT: Review a user-record workflow by confirming its relational storage context and assessing server-side permission plus transaction boundaries for a protected consistency-sensitive multi-step update.
- VARIANTS:
  - V1: Review a user-record workflow by confirming its relational storage context and assessing server-side permission plus transaction boundaries for a protected consistency-sensitive multi-step update.
  - V2: For a relational user-record service, examine how records are stored and how a protected multi-step write should be controlled by server permission and transaction boundaries.
  - V3: Assess a user-record change from storage through a protected update: identify the relational database context, decide access permission, and preserve consistency across the write.
  - V4: Prepare a service review covering relational user-record storage and a server-side permission-controlled multi-step update with the transaction boundary needed for consistency.
- EXPECTED_STATUS: COMPLETE
- EVIDENCE:
  - src_ecad6843b8fcb99b_c0000 | Access control: bearer-token identity evidence, server-side permission checks, and the JWT/server-policy caveat.
  - src_1055b8f580d99531_c0000 | Relational records: frequently used identifier filters, appropriate-index review, and consistency-sensitive transaction boundaries.
- EXPECTED_MISSING_INFORMATION: NONE
- DEPENDENCY_EXPECTATION: The authorization and consistency tasks are distinct; any shared item must be justified by both task obligations.
- NORMALIZATION_EXPECTATION: NOT_APPLICABLE
- OVERLAP_EXPECTATION: KEEP src_1055b8f580d99531_c0000 for both Task A and Task B; retain security evidence only for Task B and do not globally deduplicate the shared database context.
- NEAREST_DEV_CASE: M1-06, M1-14
- WHY_HELD_OUT: The holdout tests overlap metrics around one authorized write and distinguishes shared grounding from task merging.
- REVIEW_STATUS: HUMAN_APPROVED

## M1F-S26 — Production geography is not in the frozen corpus
- SCENARIO_ID: M1F-S26
- PRIMARY_ARCHETYPE: PARTIAL_INTENTIONAL_NO_EVIDENCE
- DOMAINS: api_architecture
- CANONICAL_SEMANTIC_INTENT: Using only the frozen service material, identify the production geography assigned to this deployment and state the evidence boundary.
- VARIANTS:
  - V1: Using only the frozen service material, identify the production geography assigned to this deployment and state the evidence boundary.
  - V2: Audit a release note request for a production region; report whether the authorized corpus names a location.
  - V3: Which deployment geography can be verified from the current evidence snapshot, if any?
  - V4: Answer the regional placement part of a service review without filling in an unstated location.
- EXPECTED_STATUS: NO_EVIDENCE
- EVIDENCE:
  - NONE | No frozen corpus chunk supports the requested fact.
- EXPECTED_MISSING_INFORMATION: The production geography is absent from all three frozen chunks; do not infer a region.
- DEPENDENCY_EXPECTATION: NOT_APPLICABLE
- NORMALIZATION_EXPECTATION: NOT_APPLICABLE
- OVERLAP_EXPECTATION: NOT_APPLICABLE
- NEAREST_DEV_CASE: M1-12
- WHY_HELD_OUT: The holdout wraps the missing fact in an evidence-boundary audit rather than repeating the direct production-region question.
- REVIEW_STATUS: HUMAN_APPROVED

## M1F-S27 — Supported token fact plus missing password policy
- SCENARIO_ID: M1F-S27
- PRIMARY_ARCHETYPE: PARTIAL_INTENTIONAL_NO_EVIDENCE
- DOMAINS: security
- CANONICAL_SEMANTIC_INTENT: Assess the security note for both its bearer-token identity flow and any stated minimum password length; separate supported from unavailable facts.
- VARIANTS:
  - V1: Assess the security note for both its bearer-token identity flow and any stated minimum password length; separate supported from unavailable facts.
  - V2: Prepare a security answer that reports what the corpus says about access tokens and whether it specifies a password-length threshold.
  - V3: Review the authentication material for a token-based identity conclusion and a possible password policy gap.
  - V4: Which part of this access-control request can be grounded, and what password requirement must remain explicitly unknown?
- EXPECTED_STATUS: PARTIAL
- EVIDENCE:
  - src_ecad6843b8fcb99b_c0000 | Access control: bearer-token identity evidence, server-side permission checks, and the JWT/server-policy caveat.
- EXPECTED_MISSING_INFORMATION: No minimum password length is available; answer the supported token/identity portion and mark the password threshold as unknown.
- DEPENDENCY_EXPECTATION: NOT_APPLICABLE
- NORMALIZATION_EXPECTATION: NOT_APPLICABLE
- OVERLAP_EXPECTATION: NOT_APPLICABLE
- NEAREST_DEV_CASE: M1-01, M1-13
- WHY_HELD_OUT: It combines one supported security fact with an intentionally absent policy field, rather than paraphrasing the missing-evidence question alone.
- REVIEW_STATUS: HUMAN_APPROVED

## M1F-S28 — API behavior plus missing SLA target
- SCENARIO_ID: M1F-S28
- PRIMARY_ARCHETYPE: PARTIAL_INTENTIONAL_NO_EVIDENCE
- DOMAINS: api_architecture
- CANONICAL_SEMANTIC_INTENT: Summarize the REST contract's validation and error behavior, then state whether the frozen material supplies an SLA target for the service.
- VARIANTS:
  - V1: Summarize the REST contract's validation and error behavior, then state whether the frozen material supplies an SLA target for the service.
  - V2: Review service evidence for request handling and report the availability objective only if it is actually documented.
  - V3: Separate the API facts that can be cited from the requested latency/availability commitment that may be missing.
  - V4: What does the frozen endpoint evidence establish, and what SLA information remains unsupported?
- EXPECTED_STATUS: PARTIAL
- EVIDENCE:
  - src_c7f92b35e6b484c5_c0000 | REST boundary: request validation, error responses, authorization requirements, and explicit dependency wording.
- EXPECTED_MISSING_INFORMATION: No latency, uptime, or other SLA target is stated in the frozen corpus; do not invent one.
- DEPENDENCY_EXPECTATION: NOT_APPLICABLE
- NORMALIZATION_EXPECTATION: NOT_APPLICABLE
- OVERLAP_EXPECTATION: NOT_APPLICABLE
- NEAREST_DEV_CASE: M1-05, M1-15
- WHY_HELD_OUT: It pairs supported API contract behavior with an absent service-level commitment in a new two-part review.
- REVIEW_STATUS: HUMAN_APPROVED

## M1F-S29 — Database evidence with unspecified schema name
- SCENARIO_ID: M1F-S29
- PRIMARY_ARCHETYPE: PARTIAL_INTENTIONAL_NO_EVIDENCE
- DOMAINS: database
- CANONICAL_SEMANTIC_INTENT: Use the database note to report storage and transaction guidance, and identify whether it names the production table or schema for those records.
- VARIANTS:
  - V1: Use the database note to report storage and transaction guidance, and identify whether it names the production table or schema for those records.
  - V2: Assess the supported relational-write facts while leaving any requested table identifier unresolved if the corpus omits it.
  - V3: Which database obligations are evidenced, and what concrete schema name cannot be verified from the snapshot?
  - V4: Prepare a bounded database review that distinguishes transaction guidance from an absent physical table detail.
- EXPECTED_STATUS: PARTIAL
- EVIDENCE:
  - src_1055b8f580d99531_c0000 | Relational records: frequently used identifier filters, appropriate-index review, and consistency-sensitive transaction boundaries.
- EXPECTED_MISSING_INFORMATION: The physical production table/schema name is absent; do not fabricate an identifier.
- DEPENDENCY_EXPECTATION: NOT_APPLICABLE
- NORMALIZATION_EXPECTATION: NOT_APPLICABLE
- OVERLAP_EXPECTATION: NOT_APPLICABLE
- NEAREST_DEV_CASE: M1-04, M1-08
- WHY_HELD_OUT: The missing item is a concrete schema identifier combined with supported storage/transaction facts, not the development data-model ordering prompt.
- REVIEW_STATUS: HUMAN_APPROVED

## M1F-S30 — Security controls with unspecified algorithm
- SCENARIO_ID: M1F-S30
- PRIMARY_ARCHETYPE: PARTIAL_INTENTIONAL_NO_EVIDENCE
- DOMAINS: security
- CANONICAL_SEMANTIC_INTENT: Report the supported bearer-token and server-authorization controls, then identify whether the frozen material names a production signing algorithm.
- VARIANTS:
  - V1: Report the supported bearer-token and server-authorization controls, then identify whether the frozen material names a production signing algorithm.
  - V2: Review the access-control evidence for its concrete security guidance and mark any requested algorithm detail that is not documented.
  - V3: Which security conclusions are grounded, and what authentication algorithm information must remain unavailable?
  - V4: Give a bounded security answer that does not infer an algorithm from the presence of bearer tokens or JWT claims.
- EXPECTED_STATUS: PARTIAL
- EVIDENCE:
  - src_ecad6843b8fcb99b_c0000 | Access control: bearer-token identity evidence, server-side permission checks, and the JWT/server-policy caveat.
- EXPECTED_MISSING_INFORMATION: No production signing or authentication algorithm is stated; do not infer one from JWT terminology.
- DEPENDENCY_EXPECTATION: NOT_APPLICABLE
- NORMALIZATION_EXPECTATION: NOT_APPLICABLE
- OVERLAP_EXPECTATION: NOT_APPLICABLE
- NEAREST_DEV_CASE: M1-02, M1-13, M1-14
- WHY_HELD_OUT: It tests an absent algorithm field alongside supported controls and explicitly guards against an unsupported JWT inference.
- REVIEW_STATUS: HUMAN_APPROVED

Human review questions: are the obligations/status complete; are the role/domain scopes correct; do the evidence refs support the intent; and are the dependency, N, O, and missing-information expectations semantically correct?
