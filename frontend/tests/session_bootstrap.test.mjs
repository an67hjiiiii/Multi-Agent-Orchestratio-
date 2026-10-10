import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { bootstrapWorkspace } from "../src/app/sessionBootstrap.mjs";

test("guest session does not request private sources or runs", async () => {
  const calls = [];
  const result = await bootstrapWorkspace({
    async currentSession() {
      calls.push("session");
      return { authenticated: false, user: null };
    },
    async health() {
      calls.push("health");
      return { ok: true };
    },
    async listSources() {
      calls.push("sources");
      return { sources: [] };
    },
    async listRuns() {
      calls.push("runs");
      return [];
    },
  });

  assert.deepEqual(calls, ["session", "health"]);
  assert.equal(result.authenticated, false);
  assert.equal(result.sources, null);
  assert.equal(result.history, null);
});

test("protected requests begin only after session restoration succeeds", async () => {
  const calls = [];
  let completeSession;
  const sessionPending = new Promise((resolve) => {
    completeSession = resolve;
  });
  const boot = bootstrapWorkspace({
    currentSession() {
      calls.push("session");
      return sessionPending;
    },
    async health() {
      calls.push("health");
      return { ok: true };
    },
    async listSources() {
      calls.push("sources");
      return { sources: [] };
    },
    async listRuns() {
      calls.push("runs");
      return [];
    },
  });

  assert.deepEqual(calls, ["session"]);
  completeSession({ authenticated: true, user: { user_id: "user-1", role: "USER" } });
  const result = await boot;

  assert.deepEqual(calls, ["session", "health", "sources", "runs"]);
  assert.equal(result.authenticated, true);
});

test("expired session skips private requests and still loads public health", async () => {
  const calls = [];
  const result = await bootstrapWorkspace({
    async currentSession() {
      calls.push("session");
      const error = new Error("expired");
      error.status = 401;
      throw error;
    },
    async health() {
      calls.push("health");
      return { ok: true };
    },
    async listSources() {
      calls.push("sources");
      return { sources: [] };
    },
    async listRuns() {
      calls.push("runs");
      return [];
    },
  });

  assert.deepEqual(calls, ["session", "health"]);
  assert.equal(result.authenticated, false);
});

test("Vite HTML shell loads the React application entry", async () => {
  const indexPath = fileURLToPath(new URL("../index.html", import.meta.url));
  const html = await readFile(indexPath, "utf8");

  assert.match(html, /<div id="root"><\/div>/);
  assert.match(html, /<script type="module" src="\/src\/main\.tsx"><\/script>/);
});
