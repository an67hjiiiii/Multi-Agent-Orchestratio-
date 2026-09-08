import type {
  ApiErrorPayload,
  ChatRequest,
  DecompositionRequest,
  HealthResponse,
  KnowledgeBaseStatus,
  PLiteInspectionResponse,
  RunListItem,
  RunRecord,
  RuntimeConfigResponse,
  SourceChunk,
  SourceDetail,
  SourceImportResult,
  SourcesResponse,
  SourceTextRequest,
} from "../types/api";

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function getErrorMessage(payload: unknown, status: number): string {
  if (isRecord(payload)) {
    const typedPayload = payload as ApiErrorPayload;
    for (const candidate of [typedPayload.message, typedPayload.detail, typedPayload.error]) {
      if (typeof candidate === "string" && candidate.trim()) return candidate;
    }
  }
  return `Request failed with HTTP ${status}`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, init);
  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    throw new ApiError(getErrorMessage(payload, response.status), response.status);
  }

  return payload as T;
}

export const api = {
  health: () => request<HealthResponse>("/health"),
  config: () => request<RuntimeConfigResponse>("/config"),
  listSources: () => request<SourcesResponse>("/sources"),
  kbStatus: () => request<KnowledgeBaseStatus>("/kb/status"),
  getSource: (sourceId: string) =>
    request<SourceDetail>(`/sources/${encodeURIComponent(sourceId)}`),
  getChunk: (chunkId: string) =>
    request<SourceChunk>(`/chunks/${encodeURIComponent(chunkId)}`),
  listRuns: () => request<RunListItem[]>("/runs"),
  getRun: (runId: string) => request<RunRecord>(`/runs/${encodeURIComponent(runId)}`),
  chat: (body: ChatRequest) =>
    request<RunRecord>("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  importText: (body: SourceTextRequest) =>
    request<SourceImportResult>("/sources/text", {
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
  decompose: (body: DecompositionRequest) =>
    request<PLiteInspectionResponse>("/tasks/decompose", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
};
