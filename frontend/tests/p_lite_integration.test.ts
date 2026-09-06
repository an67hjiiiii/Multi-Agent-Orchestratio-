import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Inspector, getPlanningInspectionResult } from "../src/components/Inspector";
import { api } from "../src/lib/api";
import type { PLiteInspectionResponse, RunRecord } from "../src/types/api";

function jsonResponse(payload: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload,
  } as Response;
}

const run: RunRecord = {
  run_id: "run_plan_001",
  query: "Review the API contract.",
  provider: "fake",
  status: "COMPLETE",
};

const inspection: PLiteInspectionResponse = {
  request: "Review the API contract.",
  tasks: [
    {
      task_id: "T1",
      title: "Inspect the API contract",
      objective: "Check request and response boundaries.",
      expected_output: "A list of contract risks.",
      domain: "api_architecture",
      role_profile: "API reviewer",
      depends_on: [],
    },
  ],
  planning_evidence_ids: ["plan-api-01"],
  status: "COMPLETE",
  warnings: [],
  planning: {
    request: "Review the API contract.",
    item_ids: ["plan-api-01"],
    scores: [0.875],
    context: "Keep request and response boundaries explicit.",
  },
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("P-lite frontend integration", () => {
  it("posts the inspection request to the documented backend boundary", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(inspection));
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      api.decompose({ request: "Review the API contract.", provider: "fake" }),
    ).resolves.toMatchObject({
      request: "Review the API contract.",
      planning_evidence_ids: ["plan-api-01"],
    });

    expect(fetchMock.mock.calls[0][0]).toBe("/api/tasks/decompose");
    expect(JSON.parse(String((fetchMock.mock.calls[0][1] as RequestInit).body))).toEqual({
      request: "Review the API contract.",
      provider: "fake",
    });
  });

  it("renders planning evidence and task inspection together", () => {
    const markup = renderToStaticMarkup(
      createElement(Inspector, {
        run,
        sources: [],
        activeTab: "plan",
        onTabChange: () => undefined,
        canInspectPlan: true,
        planningInspection: inspection,
        planningError: null,
        isInspectingPlan: false,
        onInspectPlan: () => undefined,
      }),
    );

    expect(markup).toContain("Planning evidence");
    expect(markup).toContain("plan-api-01");
    expect(markup).toContain("Task plan");
    expect(markup).toContain("Inspect the API contract");
  });

  it("falls back to top-level planning IDs when the response omits nested planning", () => {
    expect(
      getPlanningInspectionResult({
        ...inspection,
        planning: undefined,
        planning_context: "Bounded planning context",
      }),
    ).toEqual({
      request: inspection.request,
      item_ids: inspection.planning_evidence_ids,
      scores: null,
      context: "Bounded planning context",
    });
  });

  it("keeps the Plan tab and action out of the locked M0 inspector", () => {
    const markup = renderToStaticMarkup(
      createElement(Inspector, {
        run,
        sources: [],
        activeTab: "evidence",
        onTabChange: () => undefined,
        canInspectPlan: false,
      }),
    );

    expect(markup).not.toContain(">Plan</button>");
    expect(markup).not.toContain("Inspect P-lite plan");
  });
});
