import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../lib/api";
import { bootstrapWorkspace } from "./sessionBootstrap.mjs";
import type {
  HealthResponse,
  RunListItem,
  RunRecord,
  SourceImportResult,
  SourceSummary,
} from "../types/api";

export type InspectorTab = "evidence" | "sources" | "metrics";

export interface ResearchAppState {
  currentUser: { user_id: string; email?: string | null; username?: string | null; role: string } | null;
  isAuthenticated: boolean;
  health: HealthResponse | null;
  sources: SourceSummary[];
  history: RunListItem[];
  activeRun: RunRecord | null;
  pendingQuestion: string | null;
  activeTab: InspectorTab;
  isBooting: boolean;
  isRunning: boolean;
  isImporting: boolean;
  error: string | null;
  sourceNotice: string | null;
  setActiveTab: (tab: InspectorTab) => void;
  startNewRun: () => void;
  submitQuestion: (message: string, condition: string, provider: string) => Promise<void>;
  selectRun: (runId: string) => Promise<void>;
  importSource: (file: File) => Promise<SourceImportResult | null>;
  dismissError: () => void;
}
export function useResearchApp(): ResearchAppState {
  const [currentUser, setCurrentUser] = useState<ResearchAppState["currentUser"]>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [sources, setSources] = useState<SourceSummary[]>([]);
  const [history, setHistory] = useState<RunListItem[]>([]);
  const [activeRun, setActiveRun] = useState<RunRecord | null>(null);
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<InspectorTab>("evidence");
  const [isBooting, setIsBooting] = useState(true);
  const [isRunning, setIsRunning] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sourceNotice, setSourceNotice] = useState<string | null>(null);

  const refreshSources = useCallback(async () => {
    const response = await api.listSources();
    setSources(response.sources ?? []);
  }, []);

  const refreshHistory = useCallback(async () => {
    setHistory(await api.listRuns());
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function boot() {
      setIsBooting(true);
      try {
        const result = await bootstrapWorkspace(api);
        if (cancelled) return;

        setCurrentUser(result.user);
        setIsAuthenticated(result.authenticated);
        if (!result.authenticated) {
          setSources([]);
          setHistory([]);
        }
        if (result.health.status === "fulfilled") setHealth(result.health.value);
        if (result.sources?.status === "fulfilled") setSources(result.sources.value.sources ?? []);
        if (result.history?.status === "fulfilled") setHistory(result.history.value);

        const failed = [result.health, result.sources, result.history].find(
          (item) => item?.status === "rejected",
        );
        if (failed?.status === "rejected") {
          if (failed.reason instanceof ApiError && failed.reason.status === 401) {
            expireSession();
          }
          setError(failed.reason?.message ?? "Backend unavailable");
        }
      } catch (cause) {
        if (!cancelled) setError(cause instanceof Error ? cause.message : "Unable to restore the session");
      } finally {
        if (!cancelled) setIsBooting(false);
      }
    }

    void boot();
    return () => {
      cancelled = true;
    };
  }, []);

  const expireSession = useCallback(() => {
    setCurrentUser(null);
    setIsAuthenticated(false);
    setSources([]);
    setHistory([]);
    setActiveRun(null);
    setError("Your session expired. Sign in again to continue.");
  }, []);

  const submitQuestion = useCallback(
    async (message: string, condition: string, provider: string) => {
      const normalizedMessage = message.trim();
      if (!normalizedMessage) return;
      setIsRunning(true);
      setPendingQuestion(normalizedMessage);
      setError(null);
      try {
        const run = await api.chat({ message: normalizedMessage, condition, provider });
        setActiveRun(run);
        setActiveTab("evidence");
        await Promise.all([refreshHistory(), refreshSources()]);
      } catch (cause) {
        if (cause instanceof ApiError && cause.status === 401) expireSession();
        setError(cause instanceof Error ? cause.message : "Unable to run the research pipeline");
        throw cause;
      } finally {
        setIsRunning(false);
        setPendingQuestion(null);
      }
    },
    [expireSession, refreshHistory, refreshSources],
  );

  const selectRun = useCallback(async (runId: string) => {
    setPendingQuestion(null);
    setError(null);
    try {
      setActiveRun(await api.getRun(runId));
      setActiveTab("evidence");
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401) expireSession();
      setError(cause instanceof Error ? cause.message : "Unable to load this run");
    }
  }, [expireSession]);

  const importSource = useCallback(async (file: File) => {
    setIsImporting(true);
    setError(null);
    setSourceNotice(null);
    try {
      const result = await api.importFile(file);
      setSourceNotice(`${result.source_name ?? file.name} added to the corpus.`);
      await refreshSources();
      return result;
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401) expireSession();
      setError(cause instanceof Error ? cause.message : "Unable to import this source");
      return null;
    } finally {
      setIsImporting(false);
    }
  }, [expireSession, refreshSources]);

  return {
    currentUser,
    isAuthenticated,
    health,
    sources,
    history,
    activeRun,
    pendingQuestion,
    activeTab,
    isBooting,
    isRunning,
    isImporting,
    error,
    sourceNotice,
    setActiveTab,
    startNewRun: () => {
      setActiveRun(null);
      setPendingQuestion(null);
      setError(null);
      setSourceNotice(null);
    },
    submitQuestion,
    selectRun,
    importSource,
    dismissError: () => setError(null),
  };
}
