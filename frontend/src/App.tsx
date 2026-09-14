import { useEffect, useState } from "react";
import { useResearchApp } from "./app/useResearchApp";
import { api } from "./lib/api";
import { normalizeRun, type NormalizedUiRun } from "./lib/uiAdapter";
import type { AuthUser, Conversation, SourceChunk, SourceDetail, SourceSummary } from "./types/api";
import {
  AdminView,
  ChunkDialog,
  HistoryView,
  HomeView,
  KnowledgeView,
  ResearchView,
  RunInspector,
  SettingsView,
} from "./components/ProductViews";
import {
  AuthScreen,
  AppHeader,
  NavigationRail,
  type DemoSession,
  type ProductPage,
} from "./components/ProductNavigation";

function toSession(user: AuthUser): DemoSession {
  return {
    name: user.display_name || user.name || user.email || user.username || "Local researcher",
    email: user.email || user.username || "researcher@local",
    role: String(user.role).toUpperCase() === "ADMIN" ? "admin" : "researcher",
    demo: false,
  };
}

export function App() {
  const research = useResearchApp();
  const [session, setSession] = useState<DemoSession | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [authSubmitting, setAuthSubmitting] = useState(false);
  const [page, setPage] = useState<ProductPage>("home");
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [provider, setProvider] = useState("ollama");
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [inspectorTab, setInspectorTab] = useState<"run" | "evidence" | "history">("run");
  const [selectedSource, setSelectedSource] = useState<SourceDetail | null>(null);
  const [sourceLoadingId, setSourceLoadingId] = useState<string | null>(null);
  const [sourceError, setSourceError] = useState<string | null>(null);
  const [selectedChunk, setSelectedChunk] = useState<SourceChunk | null>(null);
  const [chunkError, setChunkError] = useState<string | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversation, setActiveConversation] = useState<Conversation | null>(null);
  const [conversationError, setConversationError] = useState<string | null>(null);
  const [conversationBusy, setConversationBusy] = useState(false);

  const run: NormalizedUiRun | null = research.activeRun ? normalizeRun(research.activeRun) : null;
  const chunkCount = research.sources.reduce((total, source) => total + (Number.isFinite(source.chunk_count) ? source.chunk_count : 0), 0);
  const runtimeStatus = research.isBooting
    ? "CONNECTING"
    : research.isRunning
      ? "RUNNING"
      : research.health?.ok
        ? "READY"
      : "OFFLINE";

  useEffect(() => {
    let cancelled = false;
    void api.authSession()
      .then((result) => {
        if (!cancelled && result.authenticated && result.user) setSession(toSession(result.user));
      })
      .catch(() => undefined)
      .finally(() => {
        if (!cancelled) setAuthReady(true);
      });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!session) {
      setConversations([]);
      setActiveConversation(null);
      return;
    }
    let cancelled = false;
    setConversationError(null);
    void api.listConversations()
      .then((result) => {
        if (!cancelled) setConversations(result.conversations ?? []);
      })
      .catch((cause) => {
        if (!cancelled) setConversationError(cause instanceof Error ? cause.message : "Conversation history is unavailable");
      });
    return () => { cancelled = true; };
  }, [session?.email]);

  useEffect(() => {
    const configured = research.runtimeConfig?.provider ?? research.health?.default_provider;
    if (configured === "ollama" || configured === "fake") setProvider(configured);
  }, [research.health?.default_provider, research.runtimeConfig?.provider]);

  function openInspector(tab: "run" | "evidence" | "history" = "run") {
    setInspectorTab(tab);
    setInspectorOpen(true);
  }

  async function startNewConversation() {
    research.startNewRun();
    setActiveConversation(null);
    setPage("research");
    setConversationError(null);
    try {
      const conversation = await api.createConversation();
      setActiveConversation(conversation);
      setConversations((current) => [conversation, ...current]);
    } catch (cause) {
      setConversationError(cause instanceof Error ? cause.message : "Unable to start a conversation");
    }
  }

  async function openConversation(conversationId: string) {
    setConversationBusy(true);
    setConversationError(null);
    try {
      const conversation = await api.getConversation(conversationId);
      setActiveConversation(conversation);
      setPage("research");
      research.startNewRun();
      const latestRun = [...conversation.messages].reverse().find((message) => message.run_id);
      if (latestRun?.run_id) await research.selectRun(latestRun.run_id);
    } catch (cause) {
      setConversationError(cause instanceof Error ? cause.message : "Unable to reopen this conversation");
    } finally {
      setConversationBusy(false);
    }
  }

  async function submitQuestion(message: string) {
    setPage("research");
    setConversationBusy(true);
    setConversationError(null);
    try {
      let conversation = activeConversation;
      if (!conversation) {
        conversation = await api.createConversation();
        setActiveConversation(conversation);
        setConversations((current) => [conversation as Conversation, ...current]);
      }
      const response = await api.sendConversationMessage(conversation.conversation_id, {
        message,
        condition: "A",
        provider,
      });
      setActiveConversation(response.conversation);
      setConversations((current) => current.map((item) => item.conversation_id === response.conversation.conversation_id ? response.conversation : item));
      if (response.run?.run_id) await research.selectRun(response.run.run_id);
    } catch (cause) {
      setConversationError(cause instanceof Error ? cause.message : "Unable to continue this conversation");
      throw cause;
    } finally {
      setConversationBusy(false);
    }
  }

  async function importSource(file: File) {
    await research.importSource(file);
  }

  async function selectRun(runId: string) {
    await research.selectRun(runId);
    setPage("research");
    setInspectorTab("run");
  }

  async function inspectSource(source: SourceSummary) {
    setSourceLoadingId(source.source_id);
    setSourceError(null);
    try {
      setSelectedSource(await api.getSource(source.source_id));
    } catch (cause) {
      setSelectedSource(null);
      setSourceError(cause instanceof Error ? cause.message : "Unable to load this source");
    } finally {
      setSourceLoadingId(null);
    }
  }

  function inspectKnownChunk(chunk: SourceChunk) {
    setChunkError(null);
    setSelectedChunk(chunk);
  }

  async function inspectCitation(citation: string) {
    setChunkError(null);
    setSelectedChunk(null);
    try {
      setSelectedChunk(await api.getChunk(citation));
    } catch (cause) {
      setChunkError(cause instanceof Error ? cause.message : "Unable to load this source context");
    }
  }

  async function signOut() {
    await api.logout().catch(() => undefined);
    setSession(null);
    setPage("home");
    setInspectorOpen(false);
    setSelectedSource(null);
    setSelectedChunk(null);
    setConversations([]);
    setActiveConversation(null);
  }

  async function authenticate(input: { mode: "login" | "register"; name: string; email: string; password: string }) {
    setAuthSubmitting(true);
    setAuthError(null);
    try {
      const result = input.mode === "register"
        ? await api.register({ name: input.name, email: input.email, password: input.password })
        : await api.login({ identifier: input.email, password: input.password });
      if (!result.authenticated || !result.user) throw new Error("Local authentication did not return a user session.");
      setSession(toSession(result.user));
      setPage("home");
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : "Unable to authenticate locally";
      setAuthError(message);
    } finally {
      setAuthSubmitting(false);
    }
  }

  if (!authReady) return <main className="auth-screen"><section className="auth-card" role="status"><p className="eyebrow">MERIDIAN · LOCAL EVIDENCE DESK</p><h1>Loading your local workspace…</h1><p className="auth-copy">Checking the local session without contacting a hosted service.</p></section></main>;

  if (!session) return <AuthScreen onSubmit={authenticate} error={authError} submitting={authSubmitting} />;

  return (
    <div className="product-shell">
      <NavigationRail
        page={page}
        onNavigate={setPage}
        historyCount={research.history.length}
        sourceCount={research.sources.length}
        chunkCount={chunkCount}
        session={session}
        mobileOpen={mobileNavOpen}
        onCloseMobile={() => setMobileNavOpen(false)}
        onSignOut={signOut}
      />

      <div className="product-main">
        <AppHeader
          page={page}
          session={session}
          runtimeStatus={runtimeStatus}
          health={research.health}
          run={run}
          onOpenNav={() => setMobileNavOpen(true)}
          onOpenInspector={() => openInspector("run")}
        />

        <main className="page-shell" id="main-content">
          <a className="skip-link" href="#main-content">Skip to content</a>
          {research.error && (
            <div className="notice notice-error global-notice" role="alert">
              <span><strong>Something needs attention.</strong> {research.error}</span>
              <button className="icon-button" type="button" aria-label="Dismiss notification" onClick={research.dismissError}>×</button>
            </div>
          )}
          {conversationError && <div className="notice notice-error global-notice" role="alert"><span><strong>Conversation unavailable.</strong> {conversationError}</span><button className="icon-button" type="button" aria-label="Dismiss conversation notification" onClick={() => setConversationError(null)}>×</button></div>}
          {chunkError && <div className="notice notice-error global-notice" role="alert"><span><strong>Source context unavailable.</strong> {chunkError}</span><button className="icon-button" type="button" aria-label="Dismiss source error" onClick={() => setChunkError(null)}>×</button></div>}

          {page === "home" && <HomeView sources={research.sources} history={research.history} health={research.health} onNewResearch={() => void startNewConversation()} onKnowledge={() => setPage("knowledge")} onHistory={() => setPage("history")} onSelectRun={(runId) => void selectRun(runId)} />}
          {page === "research" && <ResearchView conversation={activeConversation} run={run} pendingQuestion={research.pendingQuestion} isRunning={research.isRunning || conversationBusy} isImporting={research.isImporting} sourceNotice={research.sourceNotice} provider={provider} onProviderChange={setProvider} onSubmit={submitQuestion} onNewConversation={() => void startNewConversation()} onImport={importSource} onOpenInspector={openInspector} onOpenCitation={(citation) => { openInspector("evidence"); void inspectCitation(citation); }} />}
          {page === "knowledge" && <KnowledgeView sources={research.sources} sourceSnapshotId={research.sourceSnapshotId} knowledgeStatus={research.health?.knowledge_base} importState={research.sourceImport} isImporting={research.isImporting} selectedSource={selectedSource} sourceLoadingId={sourceLoadingId} sourceError={sourceError} onImport={importSource} onInspectSource={(source) => void inspectSource(source)} onCloseSource={() => setSelectedSource(null)} onInspectChunk={inspectKnownChunk} />}
          {page === "history" && <HistoryView conversations={conversations} activeConversationId={activeConversation?.conversation_id} onNewConversation={() => void startNewConversation()} onSelectConversation={(conversationId) => void openConversation(conversationId)} history={research.history} activeRunId={research.activeRun?.run_id} onSelectRun={(runId) => void selectRun(runId)} />}
          {page === "settings" && <SettingsView session={session} provider={provider} onSignOut={signOut} />}
          {page === "admin" && session.role === "admin" && <AdminView sources={research.sources} history={research.history} health={research.health} />}
        </main>
      </div>

      {inspectorOpen && <RunInspector run={run} history={research.history} activeTab={inspectorTab} onTabChange={setInspectorTab} onClose={() => setInspectorOpen(false)} onSelectRun={(runId) => void selectRun(runId)} onOpenCitation={(citation) => void inspectCitation(citation)} />}
      {selectedChunk && <ChunkDialog chunk={selectedChunk} onClose={() => setSelectedChunk(null)} />}
    </div>
  );
}
