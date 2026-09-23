import { afterEach, describe, expect, it, vi } from "vitest";
import { evidenceApi, normalizeRunEvidence } from "../src/features/evidence";
import { normalizeRunTrace } from "../src/features/trace";
import { traceApi } from "../src/features/trace";
import { api } from "../src/lib/api";
import type { RunEvidenceResponse, RunTraceResponse, SourceChunk } from "../src/types/api";

function jsonResponse(payload: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload,
  } as Response;
}

const chunk: SourceChunk = {
  chunk_id: "src_api_c0000",
  source_id: "src_api",
  source_name: "api.md",
  text: "The request requires a local session.",
  index: 0,
  provenance: { snapshot_id: "snapshot_1" },
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("trace and evidence API adapters", () => {
  it("wires the documented trace and evidence endpoints without changing the run id", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ run_id: "run/one", events: [], trace: [], metrics: {} }))
      .mockResolvedValueOnce(jsonResponse({ run_id: "run/one", evidence_ids: [], items: [], missing_ids: [] }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(traceApi.getRunTrace("run/one")).resolves.toMatchObject({ run_id: "run/one" });
    await expect(evidenceApi.getRunEvidence("run/one")).resolves.toMatchObject({ run_id: "run/one" });

    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      "/api/runs/run%2Fone/trace",
      "/api/runs/run%2Fone/evidence",
    ]);
  });

  it("normalizes trace aliases while preserving event fields, metrics, and raw provenance", () => {
    const response: RunTraceResponse = {
      run_id: "run_trace",
      status: "COMPLETE",
      events: [],
      trace: [{ stage: "run_finished", status: "COMPLETE", trace_detail: "kept" }],
      effective_config: { condition: "A", flags: { planning_enabled: false } },
      metrics: { latency_ms: 12 },
    };

    const snapshot = normalizeRunTrace(response);

    expect(snapshot).toMatchObject({
      runId: "run_trace",
      status: "COMPLETE",
      effectiveConfig: response.effective_config,
      metrics: { latency_ms: 12 },
      raw: response,
    });
    expect(snapshot.events).toEqual(response.trace);
    expect(snapshot.events[0]).toHaveProperty("trace_detail", "kept");
  });

  it("normalizes evidence aliases and retains unresolved canonical locators", () => {
    const response: RunEvidenceResponse = {
      run_id: "run_evidence",
      source_snapshot_id: "snapshot_1",
      evidence_ids: [chunk.chunk_id, "missing_chunk"],
      items: [],
      evidence: [chunk],
      missing_ids: ["missing_chunk"],
    };

    const snapshot = normalizeRunEvidence(response);

    expect(snapshot).toMatchObject({
      runId: "run_evidence",
      sourceSnapshotId: "snapshot_1",
      evidenceIds: [chunk.chunk_id, "missing_chunk"],
      missingIds: ["missing_chunk"],
      raw: response,
    });
    expect(snapshot.items).toEqual([chunk]);
  });

  it("keeps the shared API error envelope for trace lookup failures", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ detail: "run not found" }, 404)));

    await expect(api.getRunTrace("missing")).rejects.toMatchObject({
      name: "ApiError",
      status: 404,
      message: "run not found",
    });
  });
});
