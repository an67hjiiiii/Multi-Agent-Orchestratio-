import { describe, expect, it } from "vitest";
import type { RunRecord } from "../src/types/api";
import { normalizeRun } from "../src/lib/uiAdapter";

function baseRun(overrides: Partial<RunRecord> = {}): RunRecord {
  return {
    run_id: "run_ui_001",
    condition: "A",
    provider: "fake",
    implementation_profile: "m0",
    status: "COMPLETE",
    query: "What does the corpus say?",
    ...overrides,
  };
}

describe("normalizeRun", () => {
  it("normalizes a complete run without turning selected evidence into citations", () => {
    const run = baseRun({
      answer: "The API requires an authenticated request.",
      tasks: [
        {
          task_id: "T1",
          goal: "Answer the question",
          domain: "api",
          depends_on: [],
          evidence_needs: ["auth requirement"],
        },
      ],
      task_results: [
        {
          task_id: "T1",
          domain: "api",
          status: "COMPLETE",
          answer: "The API requires an authenticated request.",
          evidence_ids: ["src_api_c0000"],
          citations: ["src_api_c0000", "src_api_c0000"],
          invalid_citations: ["E99"],
        },
      ],
      events: [
        { stage: "run_started", ts: "2026-09-07T10:00:00Z" },
        {
          stage: "vanilla_retrieval",
          selected: ["src_api_c0000"],
          candidates: ["src_api_c0000", "src_api_c0001"],
          dropped: [{ chunk_id: "src_api_c0001", reason: "budget" }],
        },
        { stage: "run_finished", status: "COMPLETE", custom_trace_field: "kept" },
      ],
      metrics: { latency_ms: 12, citations_valid: 1 },
    });

    const normalized = normalizeRun(run);

    expect(normalized.runId).toBe("run_ui_001");
    expect(normalized.condition).toBe("A");
    expect(normalized.status).toBe("COMPLETE");
    expect(normalized.answer).toContain("authenticated");
    expect(normalized.citations).toEqual(["src_api_c0000"]);
    expect(normalized.invalidCitations).toEqual(["E99"]);
    expect(normalized.tasks[0]).toMatchObject({
      taskId: "T1",
      evidenceIds: ["src_api_c0000"],
      citations: ["src_api_c0000"],
      evidenceNeeds: ["auth requirement"],
    });
    expect(normalized.traceSummary).toMatchObject({
      eventCount: 3,
      stages: ["run_started", "vanilla_retrieval", "run_finished"],
      selectedEvidenceIds: ["src_api_c0000"],
      candidateEvidenceIds: ["src_api_c0000", "src_api_c0001"],
      droppedEvidenceIds: ["src_api_c0001"],
      selectedCount: 1,
      droppedCount: 1,
      terminalStatus: "COMPLETE",
      hasFailure: false,
    });
    expect(normalized.traceSummary.events[2]).toHaveProperty("custom_trace_field", "kept");
    expect(normalized.metrics).toEqual({ latency_ms: 12, citations_valid: 1 });
    expect(normalized.state).toEqual({
      kind: "COMPLETE",
      isNoEvidence: false,
      isError: false,
      message: "Answer ready with validated evidence.",
    });
    expect(normalized.researchFlags).toMatchObject({
      isFakeProvider: true,
      isWiringOnly: true,
      evidenceBoundary: "WIRING_ONLY",
      manualCorrectness: "UNSCORED",
      manualFaithfulness: "UNSCORED",
      isMilestoneEvidence: false,
      effectiveConfigFlags: {},
    });
    expect(normalized.raw).toBe(run);
  });

  it("keeps partial answers, valid/invalid citations, and task-scoped missing information", () => {
    const normalized = normalizeRun(
      baseRun({
        status: "PARTIAL",
        provider: "ollama",
        answer: "The available source covers indexing but not retention.",
        tasks: [
          { task_id: "T1", goal: "Review indexing", domain: "database" },
          { task_id: "T2", goal: "Review retention", domain: "database" },
        ],
        task_results: [
          {
            task_id: "T1",
            status: "COMPLETE",
            citations: ["src_db_c0000"],
            missing_information: [],
          },
          {
            task_id: "T2",
            status: "PARTIAL",
            citations: ["src_db_c0000"],
            invalid_citations: ["bad-locator"],
            missing_information: ["retention policy", "retention policy"],
          },
        ],
        effective_config: { flags: { planning_enabled: false, overlap_enabled: false } },
      }),
    );

    expect(normalized.status).toBe("PARTIAL");
    expect(normalized.citations).toEqual(["src_db_c0000"]);
    expect(normalized.invalidCitations).toEqual(["bad-locator"]);
    expect(normalized.missingInformation).toEqual(["retention policy"]);
    expect(normalized.tasks[1].missingInformation).toEqual(["retention policy"]);
    expect(normalized.state.kind).toBe("PARTIAL");
    expect(normalized.error).toBeNull();
    expect(normalized.researchFlags).toMatchObject({
      isFakeProvider: false,
      isWiringOnly: false,
      evidenceBoundary: "LOCAL_RUNTIME",
      effectiveConfigFlags: { planning_enabled: false, overlap_enabled: false },
    });
  });

  it("represents no-evidence runs distinctly and does not fabricate citations", () => {
    const run = baseRun({
      status: "NO_EVIDENCE",
      answer: "No validated evidence was found for this question.",
      tasks: [{ task_id: "T1", goal: "Find deployment region", domain: "operations" }],
      task_results: [
        {
          task_id: "T1",
          status: "NO_EVIDENCE",
          evidence_ids: [],
          citations: [],
          missing_information: ["relevant evidence"],
        },
      ],
      events: [
        { stage: "run_started" },
        { stage: "vanilla_retrieval", selected: [], candidates: [] },
        { stage: "run_finished", status: "NO_EVIDENCE" },
      ],
    });

    const normalized = normalizeRun(run);

    expect(normalized.state).toMatchObject({
      kind: "NO_EVIDENCE",
      isNoEvidence: true,
      isError: false,
    });
    expect(normalized.error).toBeNull();
    expect(normalized.citations).toEqual([]);
    expect(normalized.invalidCitations).toEqual([]);
    expect(normalized.traceSummary.selectedCount).toBe(0);
    expect(normalized.missingInformation).toEqual(["relevant evidence"]);
  });

  it("keeps a safe failed state while retaining the failure event as provenance", () => {
    const run = baseRun({
      status: "FAILED",
      error: "provider body should not become UI error text",
      events: [
        { stage: "run_started" },
        {
          stage: "run_failed",
          status: "FAILED",
          error_type: "LOCAL_MODEL_UNAVAILABLE",
          error: "provider body should not become UI error text",
        },
      ],
    });

    const normalized = normalizeRun(run);

    expect(normalized.state).toMatchObject({ kind: "FAILED", isError: true, isNoEvidence: false });
    expect(normalized.error).toEqual({
      kind: "FAILED",
      message: "The run failed before a validated answer was produced.",
      errorType: "LOCAL_MODEL_UNAVAILABLE",
    });
    expect(normalized.traceSummary).toMatchObject({
      terminalStatus: "FAILED",
      hasFailure: true,
      failure: {
        stage: "run_failed",
        errorType: "LOCAL_MODEL_UNAVAILABLE",
        hasDiagnostic: true,
      },
    });
    expect(normalized.traceSummary.events[1]).toMatchObject({
      stage: "run_failed",
      error: "provider body should not become UI error text",
    });
  });

  it("uses explicitly recorded agents and roles only", () => {
    const noAgents = normalizeRun(baseRun());
    expect(noAgents.agents).toEqual([]);
    expect(noAgents.roles).toEqual([]);

    const withAgents = normalizeRun(
      baseRun({
        agents: ["retriever", "retriever", "answerer"],
        agent_ids: ["ignored-alias-because-agents-is-present"],
        roles: ["retrieval", "answer"],
      } as RunRecord & { agents: string[]; agent_ids: string[]; roles: string[] }),
    );
    expect(withAgents.agents).toEqual(["retriever", "answerer"]);
    expect(withAgents.roles).toEqual(["retrieval", "answer"]);
    expect(withAgents.tasks).toEqual([]);
  });
});
