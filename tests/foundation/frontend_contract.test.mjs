import { describe, expect, it } from "vitest";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const foundationDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(foundationDir, "../..");
const frontendRoot = path.join(repoRoot, "frontend");
const frontendSource = path.join(frontendRoot, "src");

const documentedRoutes = new Set([
  "/api/health",
  "/api/config",
  "/api/local-model/health",
  "/api/kb/status",
  "/api/sources",
  "/api/sources/file",
  "/api/sources/text",
  "/api/chunks",
  "/api/chat",
  "/api/runs",
]);

function sourceFiles(directory) {
  if (!fs.existsSync(directory)) return [];
  const files = [];
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const absolute = path.join(directory, entry.name);
    if (entry.isDirectory()) files.push(...sourceFiles(absolute));
    else if (/\.(css|html|js|jsx|ts|tsx)$/.test(entry.name)) files.push(absolute);
  }
  return files;
}

function frontendText() {
  return sourceFiles(frontendSource)
    .map((file) => fs.readFileSync(file, "utf8"))
    .join("\n");
}

const frontendPresent = fs.existsSync(frontendSource);
const contract = frontendPresent ? describe : describe.skip;

contract("frontend API boundary", () => {
  it("uses only documented backend routes", () => {
    const routes = [...frontendText().matchAll(/['"`]\/(api\/[A-Za-z0-9._~/-]+)/g)]
      .map((match) => `/${match[1]}`)
      .map((route) => route.replace(/\/$/, ""));
    const unknown = [...new Set(routes)].filter((route) => !documentedRoutes.has(route));
    expect(unknown).toEqual([]);
  });

  it("keeps inference behind the local backend boundary", () => {
    const text = frontendText();
    expect(text).not.toMatch(/(?:https?:\/\/|127\.0\.0\.1|localhost)[^\n"'`]*/i);
    expect(text).not.toMatch(/(?:openai|anthropic|gemini|api[_-]?key|bearer)/i);
  });
});
