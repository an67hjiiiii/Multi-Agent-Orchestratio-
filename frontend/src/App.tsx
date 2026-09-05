import { useMemo, useState } from "react";
import { useResearchApp } from "./app/useResearchApp";
import { ChatPanel } from "./components/ChatPanel";
import { Inspector } from "./components/Inspector";
import { Sidebar } from "./components/Sidebar";
import { StatusBadge } from "./components/StatusBadge";

export function App() {
  const research = useResearchApp();
  const [condition, setCondition] = useState("A");
  const [provider, setProvider] = useState("fake");
  const allowedConditions = useMemo(
    () => research.health?.allowed_conditions?.length ? research.health.allowed_conditions : ["A"],
    [research.health],
  );

  async function submitQuestion(message: string) {
    await research.submitQuestion(message, condition, provider);
  }

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
          </div>
          <div className="topbar-controls">
            <label className="select-control">
              <span>Condition</span>
              <select value={condition} onChange={(event) => setCondition(event.target.value)} aria-label="Run condition">
                {allowedConditions.map((value) => <option key={value} value={value}>{value}</option>)}
              </select>
            </label>
            <label className="select-control">
              <span>Provider</span>
              <select value={provider} onChange={(event) => setProvider(event.target.value)} aria-label="Run provider">
                <option value="fake">Fake wiring</option>
                <option value="ollama">Local Ollama</option>
              </select>
            </label>
            <StatusBadge status={research.isBooting ? "CONNECTING" : research.health?.ok ? "READY" : "OFFLINE"} compact />
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
          onSubmit={submitQuestion}
          onImport={async (file) => { await research.importSource(file); }}
        />
      </div>
      <Inspector run={research.activeRun} sources={research.sources} activeTab={research.activeTab} onTabChange={research.setActiveTab} />
    </div>
  );
}
