import { describe, expect, it } from "vitest";
import { resolveWorkspaceReadiness, workspaceReadinessCopy } from "../src/features/workspace/readiness";

const base = {
  isBooting: false,
  health: {
    ok: true,
    default_provider: "fake",
    allowed_conditions: ["A"],
  },
  runtimeConfig: {
    provider: "fake",
    local_model: "qwen3:4b",
    allowed_conditions: ["A"],
  },
  knowledgeStatus: {
    status: "READY" as const,
    backend: "local_json",
    retrieval_backend: "lexical",
    source_count: 1,
    chunk_count: 1,
    snapshot_id: "corpus_1",
  },
  localModelHealth: { ok: false, message: "Ollama is not required for FakeProvider" },
};

describe("workspace readiness", () => {
  it("keeps bootstrap visibly separate from runtime readiness", () => {
    expect(resolveWorkspaceReadiness({ ...base, isBooting: true })).toBe("BOOTING");
  });

  it("reports an unavailable health response as offline", () => {
    expect(resolveWorkspaceReadiness({ ...base, health: null, issues: { health: "Health request failed" } })).toBe("OFFLINE");
  });

  it("reports an explicit empty corpus without claiming a run is ready", () => {
    const input = {
      ...base,
      knowledgeStatus: { ...base.knowledgeStatus, status: "EMPTY" as const, source_count: 0, chunk_count: 0 },
    };
    expect(resolveWorkspaceReadiness(input)).toBe("READY_EMPTY");
    expect(workspaceReadinessCopy("READY_EMPTY", input).label).toContain("empty corpus");
  });

  it("reports a ready corpus only from returned runtime and corpus facts", () => {
    expect(resolveWorkspaceReadiness(base)).toBe("READY");
  });

  it("does not claim ready when config, corpus, or the active Ollama model is unavailable", () => {
    expect(resolveWorkspaceReadiness({ ...base, runtimeConfig: null, issues: { config: "Config request failed" } })).toBe("DEGRADED");
    expect(resolveWorkspaceReadiness({ ...base, knowledgeStatus: null, issues: { corpus: "Corpus request failed" } })).toBe("DEGRADED");
    expect(resolveWorkspaceReadiness({
      ...base,
      runtimeConfig: { ...base.runtimeConfig, provider: "ollama" },
      health: { ...base.health, default_provider: "ollama" },
      localModelHealth: { ok: false, code: "LOCAL_MODEL_UNAVAILABLE" },
    })).toBe("DEGRADED");
  });

  it("keeps unknown corpus statuses conservative", () => {
    expect(resolveWorkspaceReadiness({
      ...base,
      knowledgeStatus: { ...base.knowledgeStatus, status: "FUTURE_STATE" },
    })).toBe("DEGRADED");
  });
});
