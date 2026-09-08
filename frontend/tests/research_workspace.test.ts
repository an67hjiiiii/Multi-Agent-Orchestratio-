import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { normalizeRun } from "../src/lib/uiAdapter";
import { ResearchWorkspace } from "../src/components/ResearchWorkspace";
import { buildTaskLayers } from "../src/components/TaskGraph";
import type { NormalizedUiTask } from "../src/lib/uiAdapter";

function task(taskId: string, dependsOn: string[] = []): NormalizedUiTask {
  return {
    taskId,
    goal: `${taskId} goal`,
    domain: "api",
    roleProfile: "reviewer",
    agent: null,
    dependsOn,
    evidenceNeeds: [],
    status: "COMPLETE",
    answer: null,
    evidenceIds: [],
    citations: [],
    invalidCitations: [],
    missingInformation: [],
  };
}

describe("research workspace presentation", () => {
  it("groups recorded task dependencies into readable lanes", () => {
    const layers = buildTaskLayers([
      task("T1"),
      task("T2", ["T1"]),
      task("T3", ["T1"]),
      task("T4", ["T2"]),
    ]);

    expect(layers.map((layer) => layer.map((item) => item.taskId))).toEqual([
      ["T1"],
      ["T2", "T3"],
      ["T4"],
    ]);
  });

  it("renders research topology, labels, flags, and runtime readout from explicit fields", () => {
    const run = normalizeRun({
      run_id: "run_research_ui",
      condition: "C",
      provider: "ollama",
      model: "qwen3:4b",
      implementation_profile: "m2",
      status: "COMPLETE",
      query: "Review the API and database boundary.",
      agents: ["retriever"],
      roles: ["planner"],
      tasks: [
        { task_id: "T1", goal: "Review API", domain: "api", role_profile: "API reviewer" },
        { task_id: "T2", goal: "Review database", domain: "database", depends_on: ["T1"], role_profile: "Database reviewer" },
      ],
      task_results: [
        { task_id: "T1", status: "COMPLETE", citations: ["src_api_c0000"], role_profile: "API reviewer", agent: "retriever" },
        { task_id: "T2", status: "COMPLETE", citations: ["src_db_c0000"], role_profile: "Database reviewer", agent: "retriever" },
      ],
      effective_config: { flags: { P: true, N: false, O: true } },
      metrics: { input_tokens: 120, output_tokens: 80, latency_ms: 240, llm_calls: 3, retrieved_chunks: 5, selected_chunks: 3, context_tokens_est: 96 },
      events: [{ stage: "run_finished", status: "COMPLETE" }],
    });

    const markup = renderToStaticMarkup(
      createElement(ResearchWorkspace, { run, onOpenResearch: () => undefined }),
    );

    expect(markup).toContain("Task dependency graph");
    expect(markup).toContain("T2");
    expect(markup).toContain("Database reviewer");
    expect(markup).toContain("retriever");
    expect(markup).toContain("P / N / O");
    expect(markup).toContain("Total tokens");
    expect(markup).toContain("200");
    expect(markup).toContain("Human correctness and faithfulness remain UNSCORED.");
  });
});
