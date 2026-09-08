import { afterEach, describe, expect, it, vi } from "vitest";
import { getEvidenceEvents, getEvidenceIds, getRunCitations } from "../src/components/Inspector";
import { api } from "../src/lib/api";
import type { RunRecord } from "../src/types/api";

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

describe("source and run API presentation", () => {
  it("loads the explicit knowledge-base status contract", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        status: "READY",
        backend: "local_json",
        retrieval_backend: "lexical",
        embedding_version: null,
        vector_indexed_chunks: 0,
        source_count: 1,
        chunk_count: 1,
        snapshot_id: "corpus_1",
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.kbStatus()).resolves.toMatchObject({
      status: "READY",
      retrieval_backend: "lexical",
      vector_indexed_chunks: 0,
    });
    expect(fetchMock).toHaveBeenCalledWith("/api/kb/status", undefined);
  });

  it("loads source summaries, source details, and chunks through encoded routes", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ snapshot_id: "corpus_1", sources: [] }))
      .mockResolvedValueOnce(
        jsonResponse({ source_id: "src notes", source_name: "notes.md", chunks: [] }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          chunk_id: "src notes_c0000",
          source_id: "src notes",
          source_name: "notes.md",
          text: "Evidence text",
          index: 0,
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.listSources()).resolves.toMatchObject({ snapshot_id: "corpus_1" });
    await expect(api.getSource("src notes")).resolves.toMatchObject({ source_name: "notes.md" });
    await expect(api.getChunk("src notes_c0000")).resolves.toMatchObject({ index: 0 });

    expect(fetchMock.mock.calls.map(([path]) => path)).toEqual([
      "/api/sources",
      "/api/sources/src%20notes",
      "/api/chunks/src%20notes_c0000",
    ]);
  });

  it("keeps text and file import payloads on the documented M0 routes", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({
          source_id: "src_notes",
          source_name: "notes.md",
          chunks_added: 1,
          total_chunks_for_source: 1,
          snapshot_id: "corpus_2",
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          source_id: "src_code",
          source_name: "main.py",
          chunks_added: 2,
          total_chunks_for_source: 2,
          snapshot_id: "corpus_3",
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    await api.importText({ source_name: "notes.md", text: "Evidence text" });
    await api.importFile(new File(["print('evidence')"], "main.py", { type: "text/plain" }));

    const textInit = fetchMock.mock.calls[0][1] as RequestInit;
    expect(fetchMock.mock.calls[0][0]).toBe("/api/sources/text");
    expect(textInit.method).toBe("POST");
    expect(JSON.parse(String(textInit.body))).toEqual({ source_name: "notes.md", text: "Evidence text" });

    const fileInit = fetchMock.mock.calls[1][1] as RequestInit;
    expect(fetchMock.mock.calls[1][0]).toBe("/api/sources/file");
    expect(fileInit.method).toBe("POST");
    expect(fileInit.body).toBeInstanceOf(FormData);
    expect((fileInit.body as FormData).get("file")).toBeInstanceOf(File);
  });

  it("surfaces typed run API errors without losing the HTTP status", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ detail: "run not found" }, 404));
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.getRun("run_missing")).rejects.toMatchObject({
      name: "ApiError",
      status: 404,
      message: "run not found",
    });
  });
});

describe("evidence and citation presentation", () => {
  const run: RunRecord = {
    run_id: "run_demo",
    status: "PARTIAL",
    events: [
      { stage: "vanilla_retrieval", selected: ["chunk_a"], dropped: [{ chunk_id: "chunk_b" }] },
      { stage: "run_finished", status: "PARTIAL" },
    ],
    task_results: [
      {
        task_id: "T1",
        evidence_ids: ["chunk_a", "chunk_b"],
        citations: ["chunk_a", "chunk_a"],
        invalid_citations: ["chunk_missing"],
      },
    ],
  };

  it("collects retrieval evidence across trace and task results without duplicates", () => {
    expect(getEvidenceEvents(run)).toHaveLength(1);
    expect(getEvidenceIds(run)).toEqual(["chunk_a", "chunk_b"]);
  });

  it("keeps valid and invalid citation locators visibly separate", () => {
    expect(getRunCitations(run)).toEqual({
      valid: ["chunk_a"],
      invalid: ["chunk_missing"],
    });
  });
});
