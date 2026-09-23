import type {
  ApiErrorPayload,
  AdminStatusResponse,
  AdminUsersResponse,
  AuthLoginRequest,
  AuthRegisterRequest,
  AuthSessionResponse,
  ChatRequest,
  Conversation,
  ConversationMessageResponse,
  ConversationsResponse,
  DecompositionRequest,
  HealthResponse,
  KnowledgeBaseStatus,
  LocalModelHealthResponse,
  PLiteInspectionResponse,
  RunListItem,
  RunRecord,
  RuntimeConfigResponse,
  SourceChunk,
  SourceDetail,
  SourceImportResult,
  SourcesResponse,
  SourceTextRequest,
  SettingsResponse,
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
  const response = await fetch(`/api${path}`, {
    ...init,
    credentials: init?.credentials ?? "same-origin",
  });
  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    throw new ApiError(getErrorMessage(payload, response.status), response.status);
  }

  return payload as T;
}

export const api = {
  authSession: () => request<AuthSessionResponse>("/auth/session"),
  register: (body: AuthRegisterRequest) =>
    request<AuthSessionResponse>("/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  login: (body: AuthLoginRequest) =>
    request<AuthSessionResponse>("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  logout: () =>
    request<{ ok: boolean; authenticated: boolean }>("/auth/logout", {
      method: "POST",
    }),
  adminStatus: () => request<AdminStatusResponse>("/admin/status"),
  adminUsers: () => request<AdminUsersResponse>("/admin/users"),
  health: () => request<HealthResponse>("/health"),
  config: () => request<RuntimeConfigResponse>("/config"),
  settings: () => request<SettingsResponse>("/settings"),
  localModelHealth: () => request<LocalModelHealthResponse>("/local-model/health"),
  listSources: () => request<SourcesResponse>("/sources"),
  kbStatus: () => request<KnowledgeBaseStatus>("/kb/status"),
  getSource: (sourceId: string) =>
    request<SourceDetail>(`/sources/${encodeURIComponent(sourceId)}`),
  getChunk: (chunkId: string) =>
    request<SourceChunk>(`/chunks/${encodeURIComponent(chunkId)}`),
  listRuns: () => request<RunListItem[]>("/runs"),
  getRun: (runId: string) => request<RunRecord>(`/runs/${encodeURIComponent(runId)}`),
  listConversations: () => request<ConversationsResponse>("/conversations"),
  createConversation: (title?: string) =>
    request<Conversation>("/conversations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(title ? { title } : {}),
    }),
  getConversation: (conversationId: string) =>
    request<Conversation>(`/conversations/${encodeURIComponent(conversationId)}`),
  sendConversationMessage: (conversationId: string, body: ChatRequest) =>
    request<ConversationMessageResponse>(
      `/conversations/${encodeURIComponent(conversationId)}/messages`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      },
    ),
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
