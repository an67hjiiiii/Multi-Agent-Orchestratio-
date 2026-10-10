import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../lib/api";
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
      const sessionResult = await Promise.allSettled([api.currentSession()]);

      if (cancelled) return;

      const session = sessionResult[0];
      if (session.status === "fulfilled" && session.value.authenticated) {
        setCurrentUser(session.value.user);
        setIsAuthenticated(true);
        const [healthResult, sourcesResult, historyResult] = await Promise.allSettled([
          api.health(),
          api.listSources(),
          api.listRuns(),
        ]);

        if (cancelled) return;
        if (healthResult.status === "fulfilled") setHealth(healthResult.value);
        if (sourcesResult.status === "fulfilled") setSources(sourcesResult.value.sources ?? []);
        if (historyResult.status === "fulfilled") setHistory(historyResult.value);

        const failed = [healthResult, sourcesResult, historyResult].find(
          (result) => result.status === "rejected",
        );
        if (failed?.status === "rejected") {
          if (failed.reason instanceof ApiError && failed.reason.status === 401) {
            expireSession();
          }
          setError(failed.reason?.message ?? "Backend unavailable");
        }
      } else if (session.status === "rejected" && !(session.reason instanceof ApiError && session.reason.status === 401)) {
        setError(session.reason?.message ?? "Unable to restore the session");
      } else {
        setCurrentUser(null);
        setIsAuthenticated(false);
        setSources([]);
        setHistory([]);
        const healthResult = await Promise.allSettled([api.health()]);
        if (cancelled) return;
        if (healthResult[0].status === "fulfilled") setHealth(healthResult[0].value);
      }
      setIsBooting(false);
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
      setIsRunning(true);
      setError(null);
      try {
        const run = await api.chat({ message, condition, provider });
        setActiveRun(run);
        setActiveTab("evidence");
        await Promise.all([refreshHistory(), refreshSources()]);
      } catch (cause) {
        if (cause instanceof ApiError && cause.status === 401) expireSession();
        setError(cause instanceof Error ? cause.message : "Unable to run the research pipeline");
        throw cause;
      } finally {
        setIsRunning(false);
      }
    },
    [expireSession, refreshHistory, refreshSources],
  );

  const selectRun = useCallback(async (runId: string) => {
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
    activeTab,
    isBooting,
    isRunning,
    isImporting,
    error,
    sourceNotice,
    setActiveTab,
    startNewRun: () => {
      setActiveRun(null);
      setError(null);
      setSourceNotice(null);
    },
    submitQuestion,
    selectRun,
    importSource,
    dismissError: () => setError(null),
  };
}
