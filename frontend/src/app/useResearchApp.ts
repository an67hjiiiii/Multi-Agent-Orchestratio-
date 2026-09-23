import { useCallback, useEffect, useState } from "react";
import { knowledgeApi } from "../features/knowledge/api";
import { runApi } from "../features/run/api";
import { settingsApi } from "../features/settings/api";
import {
  resolveWorkspaceReadiness,
  workspaceReadinessCopy,
  type BootstrapIssues,
  type WorkspaceReadiness,
} from "../features/workspace/readiness";
import type {
  HealthResponse,
  KnowledgeBaseStatus,
  LocalModelHealthResponse,
  PLiteInspectionResponse,
  RunListItem,
  RunRecord,
  RuntimeConfigResponse,
  SettingsResponse,
  SourceImportResult,
  SourceSummary,
} from "../types/api";

export type InspectorTab = "evidence" | "sources" | "metrics" | "plan";
export type SourceImportPhase = "idle" | "uploading" | "indexing" | "complete" | "error";

export interface SourceImportState {
  phase: SourceImportPhase;
  fileName: string | null;
  message: string | null;
  result: SourceImportResult | null;
}

const PLITE_PROFILES = new Set(["dev", "m1", "m2"]);

export interface ResearchAppState {
  health: HealthResponse | null;
  runtimeConfig: RuntimeConfigResponse | null;
  settings: SettingsResponse | null;
  knowledgeStatus: KnowledgeBaseStatus | null;
  localModelHealth: LocalModelHealthResponse | null;
  readiness: WorkspaceReadiness;
  readinessDetail: string;
  bootstrapIssues: BootstrapIssues;
  sources: SourceSummary[];
  sourceSnapshotId: string | null;
  history: RunListItem[];
  activeRun: RunRecord | null;
  pendingQuestion: string | null;
  activeTab: InspectorTab;
  isBooting: boolean;
  isRunning: boolean;
  isImporting: boolean;
  isInspectingPlan: boolean;
  sourceImport: SourceImportState;
  canInspectPlan: boolean;
  planningInspection: PLiteInspectionResponse | null;
  planningError: string | null;
  error: string | null;
  sourceNotice: string | null;
  retryBootstrap: () => Promise<void>;
  setActiveTab: (tab: InspectorTab) => void;
  startNewRun: () => void;
  submitQuestion: (message: string, condition: string, provider: string) => Promise<void>;
  selectRun: (runId: string) => Promise<void>;
  inspectPlan: (request: string, provider: string) => Promise<void>;
  importSource: (file: File) => Promise<SourceImportResult | null>;
  dismissError: () => void;
}
export function useResearchApp(): ResearchAppState {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [runtimeConfig, setRuntimeConfig] = useState<RuntimeConfigResponse | null>(null);
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [knowledgeStatus, setKnowledgeStatus] = useState<KnowledgeBaseStatus | null>(null);
  const [localModelHealth, setLocalModelHealth] = useState<LocalModelHealthResponse | null>(null);
  const [bootstrapIssues, setBootstrapIssues] = useState<BootstrapIssues>({});
  const [sources, setSources] = useState<SourceSummary[]>([]);
  const [sourceSnapshotId, setSourceSnapshotId] = useState<string | null>(null);
  const [history, setHistory] = useState<RunListItem[]>([]);
  const [activeRun, setActiveRun] = useState<RunRecord | null>(null);
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<InspectorTab>("evidence");
  const [isBooting, setIsBooting] = useState(true);
  const [isRunning, setIsRunning] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [isInspectingPlan, setIsInspectingPlan] = useState(false);
  const [planningInspection, setPlanningInspection] = useState<PLiteInspectionResponse | null>(null);
  const [planningError, setPlanningError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sourceNotice, setSourceNotice] = useState<string | null>(null);
  const [sourceImport, setSourceImport] = useState<SourceImportState>({
    phase: "idle",
    fileName: null,
    message: null,
    result: null,
  });

  const refreshSources = useCallback(async () => {
    const [response, corpus] = await Promise.all([
      knowledgeApi.listSources(),
      knowledgeApi.kbStatus(),
    ]);
    setSources(response.sources ?? []);
    setSourceSnapshotId(response.snapshot_id ?? null);
    setKnowledgeStatus(corpus);
  }, []);

  const refreshHistory = useCallback(async () => {
    setHistory(await runApi.listRuns());
  }, []);

  const bootstrap = useCallback(async () => {
    setIsBooting(true);
    setError(null);
    setBootstrapIssues({});
    setHealth(null);
    setRuntimeConfig(null);
    setSettings(null);
    setKnowledgeStatus(null);
    setLocalModelHealth(null);

    const [healthResult, configResult, corpusResult, modelResult, settingsResult, sourcesResult, historyResult] = await Promise.allSettled([
      runApi.health(),
      runApi.config(),
      knowledgeApi.kbStatus(),
      runApi.localModelHealth(),
      settingsApi.settings(),
      knowledgeApi.listSources(),
      runApi.listRuns(),
    ]);

    const issue = (result: PromiseSettledResult<unknown>) => (
      result.status === "rejected"
        ? result.reason instanceof Error ? result.reason.message : "Local request failed"
        : null
    );
    const issues: BootstrapIssues = {
      health: issue(healthResult),
      config: issue(configResult),
      corpus: issue(corpusResult),
      localModel: issue(modelResult),
      settings: issue(settingsResult),
    };
    setBootstrapIssues(issues);

    if (healthResult.status === "fulfilled") setHealth(healthResult.value);
    if (configResult.status === "fulfilled") setRuntimeConfig(configResult.value);
    if (corpusResult.status === "fulfilled") setKnowledgeStatus(corpusResult.value);
    if (modelResult.status === "fulfilled") setLocalModelHealth(modelResult.value);
    if (settingsResult.status === "fulfilled") setSettings(settingsResult.value);
    if (sourcesResult.status === "fulfilled") {
      setSources(sourcesResult.value.sources ?? []);
      setSourceSnapshotId(sourcesResult.value.snapshot_id ?? null);
    }
    if (historyResult.status === "fulfilled") setHistory(historyResult.value);

    const failed = [healthResult, configResult, corpusResult, sourcesResult, historyResult].find(
      (result) => result.status === "rejected",
    );
    if (failed?.status === "rejected") setError(failed.reason?.message ?? "Local workspace bootstrap failed");
    setIsBooting(false);
  }, []);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  const submitQuestion = useCallback(
    async (message: string, condition: string, provider: string) => {
      const normalizedMessage = message.trim();
      if (!normalizedMessage) return;

      if (condition !== "A") {
        const boundaryError = new Error("M0 supports condition A only.");
        setError(boundaryError.message);
        throw boundaryError;
      }

      if (provider !== "fake" && provider !== "ollama") {
        const providerError = new Error("Only the Fake wiring or local Ollama provider is available.");
        setError(providerError.message);
        throw providerError;
      }

      setIsRunning(true);
      setPendingQuestion(normalizedMessage);
      setError(null);
      setPlanningInspection(null);
      setPlanningError(null);
      try {
        const run = await runApi.chat({ message: normalizedMessage, condition, provider });
        setActiveRun(run);
        setActiveTab("evidence");
        await Promise.all([refreshHistory(), refreshSources()]);
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : "Unable to run the research pipeline");
        throw cause;
      } finally {
        setIsRunning(false);
        setPendingQuestion(null);
      }
    },
    [refreshHistory, refreshSources],
  );

  const selectRun = useCallback(async (runId: string) => {
    setPendingQuestion(null);
    setError(null);
    setPlanningInspection(null);
    setPlanningError(null);
    try {
      setActiveRun(await runApi.getRun(runId));
      setHistory(await runApi.listRuns());
      setActiveTab("evidence");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to load this run");
    }
  }, []);

  const inspectPlan = useCallback(
    async (request: string, provider: string) => {
      const normalizedRequest = request.trim();
      if (!normalizedRequest || !PLITE_PROFILES.has(health?.implementation_profile ?? "")) return;

      setIsInspectingPlan(true);
      setPlanningInspection(null);
      setPlanningError(null);
      try {
        setPlanningInspection(
          await runApi.decompose({ request: normalizedRequest, provider }),
        );
        setActiveTab("plan");
      } catch (cause) {
        setPlanningError(
          cause instanceof Error ? cause.message : "Unable to inspect the P-lite task plan",
        );
        setActiveTab("plan");
      } finally {
        setIsInspectingPlan(false);
      }
    },
    [health?.implementation_profile],
  );

  const importSource = useCallback(async (file: File) => {
    setIsImporting(true);
    setError(null);
    setSourceNotice(null);
    setSourceImport({ phase: "uploading", fileName: file.name, message: "Sending the file to the local source store…", result: null });
    try {
      const result = await knowledgeApi.importFile(file);
      setSourceImport({ phase: "indexing", fileName: file.name, message: "Source accepted. Refreshing indexed chunks…", result });
      setSourceNotice(`${result.source_name ?? file.name} added to the corpus.`);
      await refreshSources();
      setSourceImport({ phase: "complete", fileName: file.name, message: `${result.source_name ?? file.name} is available to local retrieval.`, result });
      return result;
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : "Unable to import this source";
      setError(message);
      setSourceImport({ phase: "error", fileName: file.name, message, result: null });
      return null;
    } finally {
      setIsImporting(false);
    }
  }, [refreshSources]);

  const readinessInput = {
    isBooting,
    health,
    runtimeConfig,
    knowledgeStatus,
    localModelHealth,
    issues: bootstrapIssues,
  };
  const readiness = resolveWorkspaceReadiness(readinessInput);
  const readinessDetail = workspaceReadinessCopy(readiness, readinessInput).detail;

  return {
    health,
    runtimeConfig,
    settings,
    knowledgeStatus,
    localModelHealth,
    readiness,
    readinessDetail,
    bootstrapIssues,
    sources,
    sourceSnapshotId,
    history,
    activeRun,
    pendingQuestion,
    activeTab,
    isBooting,
    isRunning,
    isImporting,
    error,
    sourceNotice,
    sourceImport,
    setActiveTab,
    startNewRun: () => {
      setActiveRun(null);
      setPendingQuestion(null);
      setError(null);
      setSourceNotice(null);
      setPlanningInspection(null);
      setPlanningError(null);
    },
    submitQuestion,
    selectRun,
    inspectPlan,
    importSource,
    dismissError: () => setError(null),
    retryBootstrap: bootstrap,
    isInspectingPlan,
    canInspectPlan: PLITE_PROFILES.has(health?.implementation_profile ?? ""),
    planningInspection,
    planningError,
  };
}
