import { useRef, useState } from "react";
import { useResearchApp } from "./app/useResearchApp";
import { normalizeRun } from "./lib/uiAdapter";
import { AnswerCanvas } from "./components/AnswerCanvas";
import { EvidenceDrawer, type DrawerTab } from "./components/EvidenceDrawer";
import { Sidebar } from "./components/Sidebar";
import { WorkspaceHeader, type ViewMode } from "./components/WorkspaceHeader";

const M0_CONDITION = "A";

export function App() {
  const research = useResearchApp();
  const [provider, setProvider] = useState("fake");
  const [mode, setMode] = useState<ViewMode>("normal");
  const [railOpen, setRailOpen] = useState(false);
  const railTrigger = useRef<HTMLButtonElement | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerTab, setDrawerTab] = useState<DrawerTab>("context");
  const [focusCitationId, setFocusCitationId] = useState<string | null>(null);
  const drawerTrigger = useRef<HTMLElement | null>(null);
  const normalizedRun = research.activeRun ? normalizeRun(research.activeRun) : null;

  async function submitQuestion(message: string) {
    await research.submitQuestion(message, M0_CONDITION, provider);
  }

  function openResearch() {
    drawerTrigger.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setDrawerTab("research");
    setFocusCitationId(null);
    setDrawerOpen(true);
  }

  function openSources() {
    drawerTrigger.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setDrawerTab("sources");
    setFocusCitationId(null);
    setDrawerOpen(true);
  }

  function openEvidence(citation: string, trigger: HTMLButtonElement) {
    drawerTrigger.current = trigger;
    setFocusCitationId(citation);
    setDrawerTab("context");
    setDrawerOpen(true);
  }

  function closeDrawer() {
    setDrawerOpen(false);
    setFocusCitationId(null);
    requestAnimationFrame(() => drawerTrigger.current?.focus());
  }

  const runtimeStatus = research.isBooting
    ? "CONNECTING"
    : research.isRunning
      ? "RUNNING"
      : research.health?.ok
        ? "READY"
        : "OFFLINE";

  return (
    <div className="app-shell">
      <a className="skip-link" href="#answer-canvas">Skip to answer</a>
      <Sidebar
        history={research.history}
        sources={research.sources}
        activeRunId={research.activeRun?.run_id}
        isOpen={railOpen}
        onClose={() => {
          setRailOpen(false);
          requestAnimationFrame(() => railTrigger.current?.focus());
        }}
        onNewRun={research.startNewRun}
        onSelectRun={(runId) => void research.selectRun(runId)}
        mode={mode}
        onModeToggle={() => setMode((current) => current === "normal" ? "research" : "normal")}
        provider={provider}
        model={research.runtimeConfig?.local_model ?? research.activeRun?.model ?? null}
        onProviderChange={setProvider}
        onOpenSources={openSources}
      />

      <div className="workspace-column">
        <WorkspaceHeader
          mode={mode}
          onModeChange={setMode}
          runtimeStatus={runtimeStatus}
          health={research.health}
          run={normalizedRun}
          sourceCount={research.sources.length}
          model={research.runtimeConfig?.local_model ?? research.activeRun?.model ?? null}
          onOpenRail={(trigger) => {
            railTrigger.current = trigger ?? null;
            setRailOpen(true);
          }}
          onOpenResearch={openResearch}
        />

        {research.error && (
          <div className="global-alert" role="alert">
            <span>{research.error}</span>
            <button type="button" onClick={research.dismissError} aria-label="Dismiss notification">×</button>
          </div>
        )}

        <AnswerCanvas
          run={normalizedRun}
          pendingQuestion={research.pendingQuestion}
          isRunning={research.isRunning}
          isImporting={research.isImporting}
          sourceNotice={research.sourceNotice}
          provider={provider}
          mode={mode}
          sources={research.sources}
          onProviderChange={setProvider}
          onSubmit={submitQuestion}
          onImport={async (file) => { await research.importSource(file); }}
          onOpenEvidence={openEvidence}
          onOpenResearch={openResearch}
          onOpenSources={openSources}
        />
      </div>

      <EvidenceDrawer
        open={drawerOpen}
        mode={mode}
        activeTab={drawerTab}
        onTabChange={setDrawerTab}
        onClose={closeDrawer}
        run={normalizedRun}
        sources={research.sources}
        sourceSnapshotId={research.sourceSnapshotId}
        sourceImport={research.sourceImport}
        isImporting={research.isImporting}
        onImport={async (file) => { await research.importSource(file); }}
        focusCitationId={focusCitationId}
        canInspectPlan={research.canInspectPlan}
        planningInspection={research.planningInspection}
        planningError={research.planningError}
        isInspectingPlan={research.isInspectingPlan}
        onInspectPlan={() => {
          const request = research.activeRun?.query ?? "";
          const runProvider = research.activeRun?.provider ?? provider;
          void research.inspectPlan(request, runProvider);
        }}
        knowledgeStatus={research.health?.knowledge_base}
        retrievalMode={research.runtimeConfig?.retrieval_mode}
      />
    </div>
  );
}
