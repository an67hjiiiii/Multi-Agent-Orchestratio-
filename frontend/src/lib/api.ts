import type {
  HealthResponse,
  RunListItem,
  RunRecord,
  SourceChunk,
  SourceImportResult,
  SourcesResponse,
} from "../types/api";

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, init);
  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    const detail =
      payload && typeof payload === "object" && "detail" in payload
        ? String(payload.detail)
        : `Request failed with HTTP ${response.status}`;
    throw new ApiError(detail, response.status);
  }

  return payload as T;
}

export const api = {
  health: () => request<HealthResponse>("/health"),
  listSources: () => request<SourcesResponse>("/sources"),
  getChunk: (chunkId: string) =>
    request<SourceChunk>(`/chunks/${encodeURIComponent(chunkId)}`),
  listRuns: () => request<RunListItem[]>("/runs"),
  getRun: (runId: string) => request<RunRecord>(`/runs/${encodeURIComponent(runId)}`),
  chat: (body: { message: string; condition: string; provider: string }) =>
    request<RunRecord>("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  importFile: (file: File) => {
    const body = new FormData();
    body.append("file", file);
    return request<SourceImportResult>("/sources/file", {
      method: "POST",
      body,
    });
  },
};
