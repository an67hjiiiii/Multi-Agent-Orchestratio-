import { useMemo, useState } from "react";
import { useResearchApp } from "./app/useResearchApp";
import { ChatPanel } from "./components/ChatPanel";
import { Inspector } from "./components/Inspector";
import { Sidebar } from "./components/Sidebar";
import { StatusBadge } from "./components/StatusBadge";
import { RegisterForm } from "./components/RegisterForm";
import { LoginForm } from "./components/LoginForm";
import { api, ApiError } from "./lib/api";

export function App() {
  const research = useResearchApp();
  const [condition, setCondition] = useState("A");
  const [provider, setProvider] = useState("fake");
  const [authScreen, setAuthScreen] = useState<"register" | "login" | null>(null);
  const [registrationNotice, setRegistrationNotice] = useState<string | null>(null);
  const [logoutError, setLogoutError] = useState<string | null>(null);
  const allowedConditions = useMemo(
    () => research.health?.allowed_conditions?.length ? research.health.allowed_conditions : ["A"],
    [research.health],
  );

  async function submitQuestion(message: string) {
    await research.submitQuestion(message, condition, provider);
  }

  async function signOut() {
    setLogoutError(null);
    try {
      await api.logout();
      window.location.reload();
    } catch (cause) {
      setLogoutError(cause instanceof ApiError ? cause.message : "Could not sign out. Try again.");
    }
  }

  return (
    <div className="app-shell">
      {research.isAuthenticated ? (
        <>
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
                <span className="topbar-subtitle">{research.currentUser?.email ?? research.currentUser?.username ?? "Private workspace"}</span>
              </div>
              <div className="topbar-controls">
                <button type="button" className="button-secondary" onClick={() => void signOut()}>
                  Sign out
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
            {logoutError && <div className="global-alert" role="alert">{logoutError}</div>}

            <ChatPanel
              run={research.activeRun}
              pendingQuestion={research.pendingQuestion}
              isRunning={research.isRunning}
              isImporting={research.isImporting}
              sourceNotice={research.sourceNotice}
              onSubmit={submitQuestion}
              onImport={async (file) => { await research.importSource(file); }}
            />
          </div>
          <Inspector run={research.activeRun} sources={research.sources} activeTab={research.activeTab} onTabChange={research.setActiveTab} />
        </>
      ) : (
        <main className="auth-required" aria-busy={research.isBooting}>
          <section className="auth-required-panel" aria-labelledby="auth-required-title">
            <p className="eyebrow">Local workspace</p>
            <h1 id="auth-required-title">{research.isBooting ? "Restoring your session…" : "Sign in to continue"}</h1>
            <p className="dialog-description">
              {research.isBooting
                ? "We are checking your local session before opening private sources and runs."
                : "Your sources and run history are private to your account."}
            </p>
            {research.error && <p role="alert" className="form-error">{research.error}</p>}
            {!research.isBooting && (
              <div className="form-actions">
                <button type="button" className="button-secondary" onClick={() => setAuthScreen("register")}>Create account</button>
                <button type="button" className="button-primary" onClick={() => setAuthScreen("login")}>Sign in</button>
              </div>
            )}
          </section>
        </main>
      )}
      {authScreen && (
        <div className="dialog-backdrop" onMouseDown={(event) => {
          if (event.target === event.currentTarget) setAuthScreen(null);
        }}>
          <section className="auth-dialog" role="dialog" aria-modal="true" aria-labelledby="auth-title">
            <button type="button" className="dialog-close" aria-label="Close sign in" onClick={() => setAuthScreen(null)}>×</button>
            <p className="eyebrow">Local workspace</p>
            <h1 id="auth-title">{authScreen === "register" ? "Create your account" : "Sign in"}</h1>
            <p className="dialog-description">Access your private sources and run history.</p>
            {authScreen === "register" ? (
              <>
                {registrationNotice && (
                  <div className="registration-success" role="status">
                    Account created for {registrationNotice}. Sign in to continue.
                  </div>
                )}
                <RegisterForm
                  onCancel={() => setAuthScreen(null)}
                  onRegistered={(registeredEmail) => {
                    setRegistrationNotice(registeredEmail);
                    setAuthScreen("login");
                  }}
                />
              </>
            ) : (
              <LoginForm
                onCancel={() => setAuthScreen(null)}
                onCreateAccount={() => setAuthScreen("register")}
                onSignedIn={() => window.location.reload()}
              />
            )}
          </section>
        </div>
      )}
    </div>
  );
}
