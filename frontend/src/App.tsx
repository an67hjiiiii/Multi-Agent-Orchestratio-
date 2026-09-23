import { useCallback, useEffect, useState } from "react";
import { AuthScreen, AppHeader, NavigationRail, authRestoreState, hasRememberedSession, rememberSession, toSession, type DemoSession, type ProductPage } from "./features/auth";
import { useConversationWorkspace } from "./features/conversation";
import { AdminView } from "./features/admin";
import { ChunkDialog, RunInspector, normalizeRun, type NormalizedUiRun } from "./features/evidence";
import { HistoryView } from "./features/history";
import { HomeView } from "./features/workspace";
import { KnowledgeView, useKnowledgeInspection } from "./features/knowledge";
import { ResearchView, useResearchApp } from "./features/run";
import { SettingsView } from "./features/settings";
import { authApi } from "./features/auth/api";
import { WorkspaceReadinessBanner } from "./components/WorkspaceReadinessBanner";

export function App() {
  const research = useResearchApp();
  const [session, setSession] = useState<DemoSession | null>(null);
  const [authStatus, setAuthStatus] = useState<"RESTORING" | "AUTHENTICATED" | "SIGNED_OUT" | "EXPIRED" | "ERROR">("RESTORING");
  const [authError, setAuthError] = useState<string | null>(null);
  const [authRestoreError, setAuthRestoreError] = useState<string | null>(null);
  const [authSubmitting, setAuthSubmitting] = useState(false);
  const [page, setPage] = useState<ProductPage>("home");
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [provider, setProvider] = useState<string | null>(null);
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [inspectorTab, setInspectorTab] = useState<"run" | "evidence" | "history">("run");
  const knowledge = useKnowledgeInspection();
  const conversationWorkspace = useConversationWorkspace({
    sessionKey: session?.email ?? null,
    provider,
    research,
    onNavigateToResearch: () => setPage("research"),
  });

  const run: NormalizedUiRun | null = research.activeRun ? normalizeRun(research.activeRun) : null;
  const chunkCount = research.sources.reduce((total, source) => total + (Number.isFinite(source.chunk_count) ? source.chunk_count : 0), 0);
  const runtimeStatus = research.isRunning
      ? "RUNNING"
      : research.readiness;

  const restoreSession = useCallback(async () => {
    setAuthStatus("RESTORING");
    setAuthRestoreError(null);
    try {
      const result = await authApi.authSession();
      if (result.authenticated && result.user) {
        rememberSession(true);
        setSession(toSession(result.user));
        setAuthStatus("AUTHENTICATED");
        return;
      }
      if (result.authenticated && !result.user) {
        throw new Error("Local session response did not include an authenticated user.");
      }

      const state = authRestoreState(false, hasRememberedSession());
      rememberSession(false);
      setSession(null);
      setAuthStatus(state);
    } catch (cause) {
      setSession(null);
      setAuthStatus("ERROR");
      setAuthRestoreError(cause instanceof Error ? cause.message : "Unable to restore the local session");
    }
  }, []);

  useEffect(() => {
    void restoreSession();
  }, [restoreSession]);

  useEffect(() => {
    const configured = research.runtimeConfig?.provider ?? research.health?.default_provider;
    if (typeof configured === "string" && configured.trim()) setProvider(configured);
  }, [research.health?.default_provider, research.runtimeConfig?.provider]);

  function openInspector(tab: "run" | "evidence" | "history" = "run") {
    setInspectorTab(tab);
    setInspectorOpen(true);
  }

  async function importSource(file: File) {
    await research.importSource(file);
  }

  async function selectRun(runId: string) {
    await research.selectRun(runId);
    setPage("research");
    setInspectorTab("run");
  }

  async function signOut() {
    setAuthError(null);
    try {
      await authApi.logout();
    } catch (cause) {
      setAuthError(cause instanceof Error ? cause.message : "Local sign out could not be confirmed");
    }
    rememberSession(false);
    setSession(null);
    setAuthStatus("SIGNED_OUT");
    setPage("home");
    setInspectorOpen(false);
    knowledge.closeSource();
    knowledge.closeChunk();
    conversationWorkspace.reset();
  }

  async function authenticate(input: { mode: "login" | "register"; name: string; email: string; password: string }) {
    setAuthSubmitting(true);
    setAuthError(null);
    try {
      const result = input.mode === "register"
        ? await authApi.register({ name: input.name, email: input.email, password: input.password })
        : await authApi.login({ identifier: input.email, password: input.password });
      if (!result.authenticated || !result.user) throw new Error("Local authentication did not return a user session.");
      rememberSession(true);
      setSession(toSession(result.user));
      setAuthStatus("AUTHENTICATED");
      setAuthRestoreError(null);
      setPage("home");
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : "Unable to authenticate locally";
      setAuthError(message);
    } finally {
      setAuthSubmitting(false);
    }
  }

  if (authStatus === "RESTORING") return <main className="auth-screen"><section className="auth-card" role="status" aria-live="polite"><p className="eyebrow">MERIDIAN · LOCAL EVIDENCE DESK</p><h1>Restoring your local session…</h1><p className="auth-copy">Checking the local session without contacting a hosted service.</p></section></main>;

  if (!session) return <AuthScreen onSubmit={authenticate} error={authError} restoreError={authRestoreError} status={authStatus === "ERROR" ? "ERROR" : authStatus} onRetryRestore={() => void restoreSession()} submitting={authSubmitting} />;

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
          {conversationWorkspace.conversationError && <div className="notice notice-error global-notice" role="alert"><span><strong>Conversation unavailable.</strong> {conversationWorkspace.conversationError}</span><button className="icon-button" type="button" aria-label="Dismiss conversation notification" onClick={conversationWorkspace.dismissConversationError}>×</button></div>}
          {knowledge.chunkError && <div className="notice notice-error global-notice" role="alert"><span><strong>Source context unavailable.</strong> {knowledge.chunkError}</span><button className="icon-button" type="button" aria-label="Dismiss source error" onClick={knowledge.dismissChunkError}>×</button></div>}
          <WorkspaceReadinessBanner status={research.readiness} detail={research.readinessDetail} retrying={research.isBooting} onRetry={() => void research.retryBootstrap()} />

          {page === "home" && <HomeView sources={research.sources} history={research.history} health={research.health} onNewResearch={() => void conversationWorkspace.startNewConversation()} onKnowledge={() => setPage("knowledge")} onHistory={() => setPage("history")} onSelectRun={(runId) => void selectRun(runId)} />}
          {page === "research" && <ResearchView conversation={conversationWorkspace.activeConversation} run={run} pendingQuestion={research.pendingQuestion} isRunning={research.isRunning || conversationWorkspace.conversationBusy} isImporting={research.isImporting} sourceNotice={research.sourceNotice} provider={provider} onProviderChange={setProvider} onSubmit={conversationWorkspace.submitQuestion} onNewConversation={() => void conversationWorkspace.startNewConversation()} onImport={importSource} onOpenInspector={openInspector} onOpenCitation={(citation) => { openInspector("evidence"); void knowledge.inspectCitation(citation); }} />}
          {page === "knowledge" && <KnowledgeView sources={research.sources} sourceSnapshotId={research.sourceSnapshotId} knowledgeStatus={research.knowledgeStatus ?? research.health?.knowledge_base} importState={research.sourceImport} isImporting={research.isImporting} selectedSource={knowledge.selectedSource} sourceLoadingId={knowledge.sourceLoadingId} sourceError={knowledge.sourceError} onImport={importSource} onInspectSource={(source) => void knowledge.inspectSource(source)} onCloseSource={knowledge.closeSource} onInspectChunk={knowledge.inspectKnownChunk} />}
          {page === "history" && <HistoryView conversations={conversationWorkspace.conversations} activeConversationId={conversationWorkspace.activeConversation?.conversation_id} onNewConversation={() => void conversationWorkspace.startNewConversation()} onSelectConversation={(conversationId) => void conversationWorkspace.openConversation(conversationId)} history={research.history} activeRunId={research.activeRun?.run_id} onSelectRun={(runId) => void selectRun(runId)} />}
          {page === "settings" && <SettingsView session={session} provider={provider} runtimeConfig={research.runtimeConfig} settings={research.settings} knowledgeStatus={research.knowledgeStatus} localModelHealth={research.localModelHealth} readiness={research.readiness} settingsError={research.bootstrapIssues.settings ?? null} localModelError={research.bootstrapIssues.localModel ?? null} onSignOut={signOut} />}
          {page === "admin" && session.role === "admin" && <AdminView sources={research.sources} history={research.history} health={research.health} />}
        </main>
      </div>

      {inspectorOpen && <RunInspector run={run} history={research.history} activeTab={inspectorTab} onTabChange={setInspectorTab} onClose={() => setInspectorOpen(false)} onSelectRun={(runId) => void selectRun(runId)} onOpenCitation={(citation) => void knowledge.inspectCitation(citation)} />}
      {knowledge.selectedChunk && <ChunkDialog chunk={knowledge.selectedChunk} onClose={knowledge.closeChunk} />}
    </div>
  );
}
