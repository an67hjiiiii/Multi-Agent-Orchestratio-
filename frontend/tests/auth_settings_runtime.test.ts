import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { authRestoreState } from "../src/features/auth/model";
import { AuthScreen } from "../src/components/ProductNavigation";
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

  it("renders required public registration fields without a client role control", () => {
    const markup = renderToStaticMarkup(
      createElement(AuthScreen, {
        onSubmit: async () => undefined,
        error: null,
        submitting: false,
      }),
    );

    const nameInput = markup.match(/<input[^>]*id="auth-name"[^>]*>/)?.[0] ?? "";
    expect(nameInput).toContain("required");
    expect(nameInput).not.toContain("value=");
    expect(markup).toContain('name="name"');
    expect(markup).toContain('name="email"');
    expect(markup).toContain('name="password"');
    expect(markup).toContain('type="email"');
    expect(markup).toContain("Use at least 8 characters.");
    expect(markup).not.toContain('name="role"');
    expect(markup).not.toContain("ADMIN");
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

  it("submits only public registration fields and retains duplicate-account errors", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(jsonResponse({
        authenticated: true,
        user: { id: "usr_1", user_id: "usr_1", email: "user@example.local", role: "USER" },
        session: { session_id: "ses_1", user_id: "usr_1", created_at: "now", expires_at: "later" },
      }))
      .mockResolvedValueOnce(jsonResponse({ code: "ACCOUNT_EXISTS", message: "email is already registered" }, 409));
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.register({ email: "user@example.local", name: "Local User", password: "password123" }))
      .resolves.toMatchObject({ authenticated: true, user: { role: "USER" } });
    const requestInit = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/auth/register");
    expect(requestInit.credentials).toBe("same-origin");
    expect(JSON.parse(String(requestInit.body))).toEqual({
      email: "user@example.local",
      name: "Local User",
      password: "password123",
    });

    await expect(api.register({ email: "user@example.local", name: "Local User", password: "password123" }))
      .rejects.toMatchObject({ name: "ApiError", status: 409, message: "email is already registered" });
  });
});
