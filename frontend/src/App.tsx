import { useState } from "react";
import { useResearchApp } from "./app/useResearchApp";
import { ChatPanel } from "./components/ChatPanel";
import { Inspector } from "./components/Inspector";
import { Sidebar } from "./components/Sidebar";
import { StatusBadge } from "./components/StatusBadge";

const M0_CONDITION = "A";

export function App() {
  const research = useResearchApp();
  const [provider, setProvider] = useState("fake");

  async function submitQuestion(message: string) {
    await research.submitQuestion(message, M0_CONDITION, provider);
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
      <Sidebar
        history={research.history}
        sources={research.sources}
        activeRunId={research.activeRun?.run_id}
        onNewRun={research.startNewRun}
        onSelectRun={(runId) => void research.selectRun(runId)}
      />
      <div className="workspace-column">
        <header className="topbar">
          <div className="topbar-context">
            <span className="topbar-title">Research chat</span>
            <span className="topbar-separator" aria-hidden="true">/</span>
            <span className="topbar-subtitle">Evidence-first answers</span>
            <span className="m0-context-pill">M0 · A</span>
          </div>
          <div className="topbar-controls">
            <div className="locked-control" aria-label="Run condition">
              <span>Condition</span>
              <strong>A</strong>
              <small>Vanilla RAG</small>
            </div>
            <label className="select-control">
              <span>Provider</span>
              <select
                value={provider}
                onChange={(event) => setProvider(event.target.value)}
                aria-label="Run provider"
                disabled={research.isRunning}
              >
                <option value="fake">Fake · wiring</option>
                <option value="ollama">Local Ollama</option>
              </select>
            </label>
            <StatusBadge status={runtimeStatus} compact />
          </div>
        </header>

        {research.error && (
          <div className="global-alert" role="alert">
            <span>{research.error}</span>
            <button type="button" onClick={research.dismissError} aria-label="Dismiss notification">×</button>
          </div>
        )}

        <ChatPanel
          run={research.activeRun}
          isRunning={research.isRunning}
          isImporting={research.isImporting}
          sourceNotice={research.sourceNotice}
          pendingQuestion={research.pendingQuestion}
          condition={M0_CONDITION}
          provider={provider}
          onSubmit={submitQuestion}
          onImport={async (file) => { await research.importSource(file); }}
        />
      </div>
      <Inspector
        run={research.activeRun}
        sources={research.sources}
        activeTab={research.activeTab}
        onTabChange={research.setActiveTab}
        planningInspection={research.planningInspection}
        planningError={research.planningError}
        canInspectPlan={research.canInspectPlan}
        isInspectingPlan={research.isInspectingPlan}
        onInspectPlan={() => {
          const request = research.activeRun?.query ?? "";
          const runProvider = research.activeRun?.provider ?? provider;
          void research.inspectPlan(request, runProvider);
        }}
      />
    </div>
  );
}
