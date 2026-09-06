import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { TaskResultPanel, type DecompositionResult } from "../src/components/TaskResultPanel";

const result: DecompositionResult = {
  request: "Review the auth flow and API contract.",
  planning_evidence_ids: ["plan-01"],
  status: "PARTIAL",
  warnings: ["One planning item was below the relevance threshold."],
  tasks: [
    {
      task_id: "T2",
      title: "Inspect the API contract",
      objective: "Check request and response boundaries.",
      expected_output: "A list of contract risks with locations.",
      domain: "api_architecture",
      role_profile: "API reviewer",
      depends_on: ["T1"],
    },
  ],
};

describe("TaskResultPanel", () => {
  it("renders the locked task fields, dependencies, status, and warnings accessibly", () => {
    const markup = renderToStaticMarkup(createElement(TaskResultPanel, { result }));

    expect(markup).toContain('aria-labelledby="task-result-panel-title"');
    expect(markup).toContain("Task plan");
    expect(markup).toContain("Partial");
    expect(markup).toContain("One planning item was below the relevance threshold.");
    expect(markup).toContain("Inspect the API contract");
    expect(markup).toContain("T2");
    expect(markup).toContain("Check request and response boundaries.");
    expect(markup).toContain("A list of contract risks with locations.");
    expect(markup).toContain("api_architecture");
    expect(markup).toContain("API reviewer");
    expect(markup).toContain("T1");
    expect(markup).toContain('aria-label="Dependencies for T2"');
  });

  it("renders explicit empty and error states", () => {
    const emptyMarkup = renderToStaticMarkup(createElement(TaskResultPanel));
    const errorMarkup = renderToStaticMarkup(
      createElement(TaskResultPanel, {
        result: null,
        error: "The planning run could not be loaded.",
      }),
    );

    expect(emptyMarkup).toContain('role="status"');
    expect(emptyMarkup).toContain("No task plan selected");
    expect(errorMarkup).toContain('role="alert"');
    expect(errorMarkup).toContain("Unable to load task plan");
    expect(errorMarkup).toContain("The planning run could not be loaded.");
  });

  it("explains a successful result with no task items", () => {
    const markup = renderToStaticMarkup(
      createElement(TaskResultPanel, { result: { ...result, tasks: [], warnings: [] } }),
    );

    expect(markup).toContain("No tasks returned");
    expect(markup).toContain("The planning result contains no task items.");
  });
});
