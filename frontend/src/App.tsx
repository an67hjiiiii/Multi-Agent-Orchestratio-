import { useMemo, useState } from "react";
import { useResearchApp } from "./app/useResearchApp";
import { ChatPanel } from "./components/ChatPanel";
import { Inspector } from "./components/Inspector";
import { Sidebar } from "./components/Sidebar";
import { StatusBadge } from "./components/StatusBadge";
import { RegisterForm } from "./components/RegisterForm";

export function App() {
  const research = useResearchApp();
  const [condition, setCondition] = useState("A");
  const [provider, setProvider] = useState("fake");
  const [showRegister, setShowRegister] = useState(false);
  const [registrationNotice, setRegistrationNotice] = useState<string | null>(null);
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
            <button type="button" className="button-secondary" onClick={() => setShowRegister(true)}>
              Create account
            </button>
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
      {showRegister && (
        <div className="dialog-backdrop" onMouseDown={(event) => {
          if (event.target === event.currentTarget) setShowRegister(false);
        }}>
          <section className="auth-dialog" role="dialog" aria-modal="true" aria-labelledby="register-title">
            <button type="button" className="dialog-close" aria-label="Close registration" onClick={() => setShowRegister(false)}>×</button>
            <p className="eyebrow">Local workspace</p>
            <h1 id="register-title">Create your account</h1>
            <p className="dialog-description">Your sources and runs will be kept in your private workspace.</p>
            {registrationNotice ? (
              <div className="registration-success" role="status">
                Account created for {registrationNotice}. You can sign in next.
              </div>
            ) : (
              <RegisterForm
                onCancel={() => setShowRegister(false)}
                onRegistered={(registeredEmail) => setRegistrationNotice(registeredEmail)}
              />
            )}
          </section>
        </div>
      )}
    </div>
  );
}
