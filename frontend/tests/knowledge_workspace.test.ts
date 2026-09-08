import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { KnowledgeWorkspace } from "../src/components/KnowledgeWorkspace";
import { sourceType } from "../src/components/KnowledgeSourceList";
import { api } from "../src/lib/api";
import type { SourceImportState } from "../src/app/useResearchApp";

function jsonResponse(payload: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload,
  } as Response;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("knowledge workspace", () => {
  it("derives readable source types without changing the API shape", () => {
    expect(sourceType("research-notes.md")).toBe("Markdown");
    expect(sourceType("retriever.py")).toBe("Code");
    expect(sourceType("corpus.data")).toBe("Text");
  });

  it("renders source availability, indexing facts, snapshot, and import progress", () => {
    const sourceImport: SourceImportState = {
      phase: "complete",
      fileName: "research-notes.md",
      message: "research-notes.md is available to local retrieval.",
      result: {
        source_id: "src_notes",
        source_name: "research-notes.md",
        chunks_added: 2,
        total_chunks_for_source: 2,
        snapshot_id: "corpus_1234567890",
      },
    };
    const markup = renderToStaticMarkup(
      createElement(KnowledgeWorkspace, {
        sources: [{ source_id: "src_notes", source_name: "research-notes.md", chunk_count: 2 }],
        sourceSnapshotId: "corpus_1234567890",
        sourceImport,
        isImporting: false,
        onImport: async () => undefined,
        onInspectChunk: () => undefined,
      }),
    );

    expect(markup).toContain("Corpus workspace");
    expect(markup).toContain("Available locally");
    expect(markup).toContain("Indexed");
    expect(markup).toContain("Markdown");
    expect(markup).toContain("Source ready");
    expect(markup).toContain("Index chunks");
    expect(markup).toContain("corpus_1234567890");
  });

  it("keeps the runtime configuration endpoint typed and frontend-only", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        implementation_profile: "m0",
        provider: "fake",
        local_model: "qwen3:4b",
        allowed_conditions: ["A"],
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.config()).resolves.toMatchObject({ local_model: "qwen3:4b" });
    expect(fetchMock.mock.calls[0][0]).toBe("/api/config");
  });
});
