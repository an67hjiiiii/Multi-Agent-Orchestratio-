import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { authRestoreState } from "../src/features/auth/model";
import { SettingsView } from "../src/components/ProductViews";
import { api } from "../src/lib/api";

function jsonResponse(payload: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload,
  } as Response;
}

describe("local auth restore and runtime settings", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });
  it("distinguishes a signed-out response from an expired remembered session", () => {
    expect(authRestoreState(false, false)).toBe("SIGNED_OUT");
    expect(authRestoreState(false, true)).toBe("EXPIRED");
    expect(authRestoreState(true, true)).toBe("AUTHENTICATED");
  });

  it("renders returned settings and local-model diagnostics without a provider fallback", () => {
    const markup = renderToStaticMarkup(
      createElement(SettingsView, {
        session: { name: "Local researcher", email: "researcher@local", role: "researcher", demo: false },
        provider: null,
        runtimeConfig: null,
        settings: {
          local_only: true,
          runtime: {
            provider: "ollama",
            local_model: "qwen3:4b",
            retrieval_mode: "LEXICAL",
            config_hash: "cfg_123",
          },
          knowledge_base: {
            status: "READY",
            backend: "local_json",
            source_count: 1,
            chunk_count: 2,
            snapshot_id: "corpus_1",
          },
        },
        knowledgeStatus: null,
        localModelHealth: { ok: false, code: "LOCAL_MODEL_UNAVAILABLE", message: "Local Ollama health check failed" },
        readiness: "DEGRADED",
        settingsError: null,
        localModelError: null,
        onSignOut: () => undefined,
      }),
    );

    expect(markup).toContain("Returned configuration");
    expect(markup).toContain("ollama");
    expect(markup).toContain("qwen3:4b");
    expect(markup).toContain("LEXICAL");
    expect(markup).toContain("cfg_123");
    expect(markup).toContain("Unavailable");
    expect(markup).toContain("Local Ollama health check failed");
    expect(markup).not.toContain("Runtime-selected local provider");
  });

  it("keeps settings and local-model routes on the existing API boundary", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(jsonResponse({ local_only: true, runtime: { provider: "fake" } }))
      .mockResolvedValueOnce(jsonResponse({ ok: false, code: "LOCAL_MODEL_UNAVAILABLE" }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.settings()).resolves.toMatchObject({ local_only: true });
    await expect(api.localModelHealth()).resolves.toMatchObject({ ok: false });
    expect(fetchMock.mock.calls.map(([path]) => path)).toEqual([
      "/api/settings",
      "/api/local-model/health",
    ]);
  });
});
