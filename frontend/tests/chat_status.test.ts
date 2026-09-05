import { describe, expect, it } from "vitest";
import type { RunRecord } from "../src/types/api";
import { formatMetricValue, getChatStatus } from "../src/components/ChatPanel";
import { getStatusLabel, getStatusTone } from "../src/components/StatusBadge";

const run = (status: string): RunRecord => ({
  run_id: "run-m0-001",
  status,
});

describe("M0/A chat status and runtime display", () => {
  it("prioritizes the pending state and preserves terminal API statuses", () => {
    expect(getChatStatus(null, true)).toBe("RUNNING");
    expect(getChatStatus(run("COMPLETE"), false)).toBe("COMPLETE");
    expect(getChatStatus(run("NO_EVIDENCE"), false)).toBe("NO_EVIDENCE");
  });

  it("uses stable tones and human-readable labels for terminal states", () => {
    expect(getStatusTone("NO_EVIDENCE")).toBe("no-evidence");
    expect(getStatusLabel("PARTIAL")).toBe("Partial");
    expect(getStatusTone("UNEXPECTED_STATE")).toBe("unknown");
  });

  it("formats missing and measured runtime values explicitly", () => {
    expect(formatMetricValue(undefined)).toBe("—");
    expect(formatMetricValue(42, " ms")).toContain("42");
    expect(formatMetricValue(42, " ms")).toContain(" ms");
  });
});
