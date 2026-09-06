import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import {
  formatPlanningScore,
  getPlanningEvidenceState,
  PlanningEvidencePanel,
  type PlanningRetrievalResult,
} from "../src/components/PlanningEvidencePanel";

const availableResult: PlanningRetrievalResult = {
  item_ids: ["planning_security", "planning_api"],
  scores: [0.875, 0.42],
  context: "[planning_security] Keep authentication and authorization obligations separate.",
};

describe("planning evidence panel", () => {
  it("keeps planning evidence distinct and pairs supplied retrieval scores with IDs", () => {
    const markup = renderToStaticMarkup(createElement(PlanningEvidencePanel, { result: availableResult }));

    expect(markup).toContain('aria-label="Planning evidence"');
    expect(markup).toContain("Planning evidence guides decomposition only");
    expect(markup).toContain("distinct from answer-domain evidence");
    expect(markup).toContain("planning_security");
    expect(markup).toContain("planning_api");
    expect(markup).toContain("0.875");
    expect(markup).toContain("0.420");
    expect(markup).toContain("Available");
  });

  it("shows a weak state when IDs exist without bounded planning context", () => {
    const result: PlanningRetrievalResult = {
      item_ids: ["planning_database"],
      scores: null,
      context: "",
    };
    const markup = renderToStaticMarkup(createElement(PlanningEvidencePanel, { result }));

    expect(getPlanningEvidenceState(result)).toBe("WEAK");
    expect(markup).toContain("Weak planning evidence");
    expect(markup).toContain("Not available");
    expect(markup).toContain("Not supplied");
    expect(markup).toContain("bounded planning context is unavailable");
  });

  it("shows an explicit no-evidence state for a missing result", () => {
    const markup = renderToStaticMarkup(createElement(PlanningEvidencePanel));

    expect(getPlanningEvidenceState(null)).toBe("NO_EVIDENCE");
    expect(markup).toContain("No planning evidence");
    expect(markup).toContain("No planning evidence IDs were returned.");
    expect(markup).toContain("No IDs");
    expect(markup).toContain("Not available");
  });

  it("formats only finite numeric retrieval scores", () => {
    expect(formatPlanningScore(0.5)).toBe("0.500");
    expect(formatPlanningScore(null)).toBe("—");
    expect(formatPlanningScore(Number.NaN)).toBe("—");
  });
});
