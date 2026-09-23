import type {
  HealthResponse,
  KnowledgeBaseStatus,
  LocalModelHealthResponse,
  RuntimeConfigResponse,
} from "../../types/api";

export type WorkspaceReadiness =
  | "BOOTING"
  | "OFFLINE"
  | "DEGRADED"
  | "READY_EMPTY"
  | "READY";

export interface BootstrapIssues {
  health?: string | null;
  config?: string | null;
  corpus?: string | null;
  localModel?: string | null;
  settings?: string | null;
}

export interface WorkspaceReadinessInput {
  isBooting: boolean;
  health: HealthResponse | null;
  runtimeConfig: RuntimeConfigResponse | null;
  knowledgeStatus: KnowledgeBaseStatus | null;
  localModelHealth: LocalModelHealthResponse | null;
  issues?: BootstrapIssues;
}

export interface WorkspaceReadinessCopy {
  label: string;
  detail: string;
}

const READY_PROVIDERS = new Set(["fake", "ollama"]);

export function resolveWorkspaceReadiness({
  isBooting,
  health,
  runtimeConfig,
  knowledgeStatus,
  localModelHealth,
  issues = {},
}: WorkspaceReadinessInput): WorkspaceReadiness {
  if (isBooting) return "BOOTING";

  if (issues.health || !health) return "OFFLINE";
  if (health.ok !== true) return "OFFLINE";

  if (issues.config || !runtimeConfig) return "DEGRADED";

  const provider = String(runtimeConfig.provider ?? health.default_provider ?? "").trim().toLowerCase();
  if (!provider || !READY_PROVIDERS.has(provider)) return "DEGRADED";
  if (!runtimeConfig.allowed_conditions?.length && !health.allowed_conditions?.length) {
    return "DEGRADED";
  }

  if (issues.corpus) return "DEGRADED";
  const corpus = knowledgeStatus ?? health.knowledge_base;
  if (!corpus) return "DEGRADED";

  const corpusStatus = String(corpus.status ?? "").trim().toUpperCase();
  if (corpusStatus === "FAILED" || corpusStatus === "UNAVAILABLE") return "DEGRADED";
  if (corpusStatus !== "EMPTY" && corpusStatus !== "READY") return "DEGRADED";

  // FakeProvider is a wiring/test double. Its local-model diagnostic is useful
  // context, but it is not an active capability for that returned provider.
  if (provider === "ollama") {
    if (issues.localModel || !localModelHealth || localModelHealth.ok !== true) {
      return "DEGRADED";
    }
  }

  return corpusStatus === "EMPTY" ? "READY_EMPTY" : "READY";
}

export function workspaceReadinessCopy(
  status: WorkspaceReadiness,
  input: WorkspaceReadinessInput,
): WorkspaceReadinessCopy {
  switch (status) {
    case "BOOTING":
      return {
        label: "Booting",
        detail: "Reading the local runtime, configuration, and corpus status.",
      };
    case "OFFLINE":
      return {
        label: "Offline",
        detail: input.issues?.health || "The local service did not return a healthy runtime response.",
      };
    case "DEGRADED":
      if (input.issues?.config) {
        return { label: "Degraded", detail: input.issues.config };
      }
      if (input.issues?.corpus) {
        return { label: "Degraded", detail: input.issues.corpus };
      }
      if (input.issues?.localModel || input.localModelHealth?.ok === false) {
        return {
          label: "Degraded",
          detail: input.localModelHealth?.message || input.localModelHealth?.error || input.issues?.localModel || "The configured local model is unavailable.",
        };
      }
      return {
        label: "Degraded",
        detail: "Some returned runtime capability is unavailable; no provider fallback is active.",
      };
    case "READY_EMPTY":
      return {
        label: "Ready · empty corpus",
        detail: "The local runtime is available. Add a source before asking for grounded evidence.",
      };
    case "READY":
      return {
        label: "Ready",
        detail: "The returned local runtime and corpus status are ready for the workspace.",
      };
  }
}
