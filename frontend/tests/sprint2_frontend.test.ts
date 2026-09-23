import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { AppHeader, type DemoSession } from "../src/components/ProductNavigation";
import { RunInspector } from "../src/components/ProductViews";
import { normalizeRun } from "../src/lib/uiAdapter";
import type { PLiteInspectionResponse, RunRecord } from "../src/types/api";

const session: DemoSession = {
  name: "Local researcher",
  email: "researcher@local",
  role: "researcher",
  demo: false,
};

const run = normalizeRun({
  run_id: "run-sprint2",
  query: "Review the retrieval contract.",
  provider: "fake",
  status: "COMPLETE",
  answer: "The contract keeps source provenance explicit.",
} satisfies RunRecord);

const planning: PLiteInspectionResponse = {
  request: "Review the retrieval contract.",
  tasks: [
    {
      task_id: "T1",
      title: "Inspect the contract",
      objective: "Check request and response boundaries.",
      expected_output: "A bounded contract review.",
      domain: "api_architecture",
      role_profile: "API reviewer",
      depends_on: [],
    },
  ],
  planning_evidence_ids: ["plan-contract-01"],
  status: "COMPLETE",
  warnings: [],
};

describe("Sprint 2 product surface", () => {
  it("renders an accessible Normal and Research / Demo mode switch", () => {
    const markup = renderToStaticMarkup(
      createElement(AppHeader, {
        page: "research",
        session,
        runtimeStatus: "READY",
        health: null,
        run,
        mode: "normal",
        onModeChange: () => undefined,
        onOpenNav: () => undefined,
        onOpenInspector: () => undefined,
      }),
    );

    expect(markup).toContain('aria-label="Presentation mode"');
    expect(markup).toContain("Normal");
    expect(markup).toContain("Research / Demo");
    expect(markup).toContain('aria-pressed="true"');
  });

  it("mounts the P-lite plan tab only when planning inspection is enabled", () => {
    const markup = renderToStaticMarkup(
      createElement(RunInspector, {
        run,
        history: [],
        activeTab: "plan",
        onTabChange: () => undefined,
        onClose: () => undefined,
        onSelectRun: () => undefined,
        onOpenCitation: () => undefined,
        canInspectPlan: true,
        planningInspection: planning,
        planningError: null,
        isInspectingPlan: false,
        onInspectPlan: () => undefined,
      }),
    );

    expect(markup).toContain("P-lite planning inspector");
    expect(markup).toContain("Planning evidence");
    expect(markup).toContain("Task plan");
    expect(markup).toContain("plan-contract-01");
  });
});
