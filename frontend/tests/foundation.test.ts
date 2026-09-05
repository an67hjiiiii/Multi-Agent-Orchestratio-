import { describe, expect, it } from "vitest";
import { readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const sourceRoot = fileURLToPath(new URL("../src", import.meta.url));
const documentedRoutes = new Set([
  "/api/health",
  "/api/config",
  "/api/local-model/health",
  "/api/sources",
  "/api/sources/file",
  "/api/sources/text",
  "/api/chunks",
  "/api/chat",
  "/api/runs",
]);

function sourceText(directory: string): string {
  return readdirSync(directory, { withFileTypes: true })
    .flatMap((entry) => {
      const path = resolve(directory, entry.name);
      if (entry.isDirectory()) return sourceText(path);
      return /\.(css|html|js|jsx|ts|tsx)$/.test(entry.name)
        ? [readFileSync(path, "utf8")]
        : [];
    })
    .join("\n");
}

describe("frontend foundation boundary", () => {
  const text = sourceText(sourceRoot);

  it("uses only documented backend routes", () => {
    const routes = [...text.matchAll(/[\"'`]\/(api\/[A-Za-z0-9._~/-]+)/g)]
      .map((match) => `/${match[1]}`.replace(/\/$/, ""));
    expect([...new Set(routes)].filter((route) => !documentedRoutes.has(route))).toEqual([]);
  });

  it("keeps inference behind the local backend boundary", () => {
    expect(text).not.toMatch(/(?:https?:\/\/|127\.0\.0\.1|localhost)[^\n"'`]*/i);
    expect(text).not.toMatch(/(?:openai|anthropic|gemini|api[_-]?key|bearer)/i);
  });
});
