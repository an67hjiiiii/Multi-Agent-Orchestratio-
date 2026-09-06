import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import type {
  HealthResponse,
  PLiteInspectionResponse,
  RunListItem,
  RunRecord,
  SourceImportResult,
  SourceSummary,
} from "../types/api";

export type InspectorTab = "evidence" | "sources" | "metrics" | "plan";

const PLITE_PROFILES = new Set(["dev", "m1", "m2"]);

export interface ResearchAppState {
  health: HealthResponse | null;
  sources: SourceSummary[];
  history: RunListItem[];
  activeRun: RunRecord | null;
  pendingQuestion: string | null;
  activeTab: InspectorTab;
  isBooting: boolean;
  isRunning: boolean;
  isImporting: boolean;
  isInspectingPlan: boolean;
  canInspectPlan: boolean;
  planningInspection: PLiteInspectionResponse | null;
  planningError: string | null;
  error: string | null;
  sourceNotice: string | null;
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
  const [sources, setSources] = useState<SourceSummary[]>([]);
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
      if (failed?.status === "rejected") setError(failed.reason?.message ?? "Backend unavailable");
      setIsBooting(false);
    }

    void boot();
    return () => {
      cancelled = true;
    };
  }, []);

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
        const run = await api.chat({ message: normalizedMessage, condition, provider });
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
      setActiveRun(await api.getRun(runId));
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
          await api.decompose({ request: normalizedRequest, provider }),
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
    try {
      const result = await api.importFile(file);
      setSourceNotice(`${result.source_name ?? file.name} added to the corpus.`);
      await refreshSources();
      return result;
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to import this source");
      return null;
    } finally {
      setIsImporting(false);
    }
  }, [refreshSources]);

  return {
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
      setPlanningInspection(null);
      setPlanningError(null);
    },
    submitQuestion,
    selectRun,
    inspectPlan,
    importSource,
    dismissError: () => setError(null),
    isInspectingPlan,
    canInspectPlan: PLITE_PROFILES.has(health?.implementation_profile ?? ""),
    planningInspection,
    planningError,
  };
}
