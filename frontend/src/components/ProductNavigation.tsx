import { useState } from "react";
import type { HealthResponse, RunStatus } from "../types/api";
import type { NormalizedUiRun } from "../lib/uiAdapter";
import { StatusBadge } from "./StatusBadge";

export type ProductPage = "home" | "research" | "knowledge" | "history" | "settings" | "admin";

export interface DemoSession {
  name: string;
  email: string;
  role: "researcher" | "admin";
  demo: boolean;
}

interface AuthScreenProps {
  onSubmit: (input: { mode: "login" | "register"; name: string; email: string; password: string }) => Promise<void>;
  error: string | null;
  submitting: boolean;
}

export function AuthScreen({ onSubmit, error, submitting }: AuthScreenProps) {
  const [mode, setMode] = useState<"login" | "register">("register");

  return (
    <main className="auth-screen">
      <section className="auth-card" aria-labelledby="auth-title">
        <div className="auth-mark" aria-hidden="true">M</div>
        <p className="eyebrow">MERIDIAN · LOCAL EVIDENCE DESK</p>
        <h1 id="auth-title">A clear path from question to evidence.</h1>
        <p className="auth-copy">{mode === "register" ? "Create a local account for asking focused questions against a corpus stored on this machine." : "Sign in to your local research workspace."}</p>
        <div className="auth-mode-toggle" role="tablist" aria-label="Account access mode">
          <button type="button" role="tab" aria-selected={mode === "register"} className={`auth-mode-button${mode === "register" ? " auth-mode-button-active" : ""}`} onClick={() => setMode("register")}>Register</button>
          <button type="button" role="tab" aria-selected={mode === "login"} className={`auth-mode-button${mode === "login" ? " auth-mode-button-active" : ""}`} onClick={() => setMode("login")}>Login</button>
        </div>
        <form
          className="auth-form"
          onSubmit={(event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            void onSubmit({
              mode,
              name: String(form.get("name") || "Local researcher").trim() || "Local researcher",
              email: String(form.get("email") || "").trim(),
              password: String(form.get("password") || ""),
            });
          }}
        >
          {mode === "register" && <><label htmlFor="auth-name">Your name</label><input id="auth-name" name="name" type="text" autoComplete="name" defaultValue="Local researcher" /></>}
          <label htmlFor="auth-email">Workspace email</label>
          <input id="auth-email" name="email" type="email" autoComplete={mode === "register" ? "email" : "username"} placeholder="you@local" required />
          <label htmlFor="auth-password">Password</label>
          <input id="auth-password" name="password" type="password" autoComplete={mode === "register" ? "new-password" : "current-password"} minLength={8} required />
          {error && <div className="notice notice-error" role="alert">{error}</div>}
          <button className="button button-primary auth-submit" type="submit" disabled={submitting}>{submitting ? "Connecting locally…" : mode === "register" ? "Create local account" : "Sign in locally"} <span aria-hidden="true">→</span></button>
        </form>
        <p className="auth-boundary"><span aria-hidden="true">◉</span> Local-only account · credentials stay in the local auth store</p>
      </section>
    </main>
  );
}

interface NavigationRailProps {
  page: ProductPage;
  onNavigate: (page: ProductPage) => void;
  historyCount: number;
  sourceCount: number;
  chunkCount: number;
  session: DemoSession;
  mobileOpen: boolean;
  onCloseMobile: () => void;
  onSignOut: () => void;
}

function NavIcon({ children }: { children: string }) {
  return <span className="nav-icon" aria-hidden="true">{children}</span>;
}

export function NavigationRail({
  page,
  onNavigate,
  historyCount,
  sourceCount,
  chunkCount,
  session,
  mobileOpen,
  onCloseMobile,
  onSignOut,
}: NavigationRailProps) {
  const navigate = (nextPage: ProductPage) => {
    onNavigate(nextPage);
    onCloseMobile();
  };

  return (
    <>
      {mobileOpen && <button className="nav-backdrop" type="button" aria-label="Close navigation" onClick={onCloseMobile} />}
      <aside className={`navigation-rail${mobileOpen ? " navigation-rail-open" : ""}`} aria-label="Primary navigation">
        <div className="brand-lockup">
          <span className="brand-symbol" aria-hidden="true">M</span>
          <span>
            <strong>Meridian</strong>
            <small>Local evidence desk</small>
          </span>
        </div>

        <button className="button button-primary new-research-button" type="button" onClick={() => navigate("research")}>
          <span aria-hidden="true">＋</span> New research
        </button>

        <nav className="primary-nav" aria-label="Workspace">
          <p className="nav-section-label">Workspace</p>
          <NavItem active={page === "home"} onClick={() => navigate("home")} icon="⌂" label="Home" />
          <NavItem active={page === "knowledge"} onClick={() => navigate("knowledge")} icon="▦" label="Knowledge Base" detail={`${sourceCount} sources`} />
          <NavItem active={page === "history"} onClick={() => navigate("history")} icon="↺" label="History" detail={`${historyCount} runs`} />
        </nav>

        <nav className="primary-nav nav-lower" aria-label="Account">
          <p className="nav-section-label">Account</p>
          <NavItem active={page === "settings"} onClick={() => navigate("settings")} icon="⚙" label="Settings" />
          {session.role === "admin" && (
            <NavItem active={page === "admin"} onClick={() => navigate("admin")} icon="◆" label="Admin" detail="Local access" />
          )}
        </nav>

        <div className="rail-summary" aria-label="Local corpus summary">
          <div className="rail-summary-heading"><span>Corpus</span><span className="summary-live-dot" aria-hidden="true" /></div>
          <strong>{sourceCount} {sourceCount === 1 ? "source" : "sources"}</strong>
          <small>{chunkCount} indexed {chunkCount === 1 ? "chunk" : "chunks"}</small>
          <button type="button" onClick={() => navigate("knowledge")}>Browse sources <span aria-hidden="true">→</span></button>
        </div>

        <div className="account-card">
          <div className="account-avatar" aria-hidden="true">{session.name.slice(0, 1).toUpperCase()}</div>
          <div className="account-copy"><strong>{session.name}</strong><small>{session.demo ? "Local demo session" : session.email}</small></div>
          <button className="icon-button account-menu-button" type="button" aria-label="Sign out" title="Sign out" onClick={onSignOut}>↪</button>
        </div>
      </aside>
    </>
  );
}

function NavItem({
  active,
  onClick,
  icon,
  label,
  detail,
}: {
  active: boolean;
  onClick: () => void;
  icon: string;
  label: string;
  detail?: string;
}) {
  return (
    <button className={`nav-item${active ? " nav-item-active" : ""}`} type="button" aria-current={active ? "page" : undefined} onClick={onClick}>
      <NavIcon>{icon}</NavIcon>
      <span className="nav-item-label">{label}</span>
      {detail && <small>{detail}</small>}
    </button>
  );
}

interface AppHeaderProps {
  page: ProductPage;
  session: DemoSession;
  runtimeStatus: RunStatus | string;
  health: HealthResponse | null;
  run: NormalizedUiRun | null;
  onOpenNav: () => void;
  onOpenInspector: () => void;
}

const pageTitles: Record<ProductPage, string> = {
  home: "Home",
  research: "New research",
  knowledge: "Knowledge Base",
  history: "History",
  settings: "Settings",
  admin: "Admin",
};

export function AppHeader({ page, session, runtimeStatus, health, run, onOpenNav, onOpenInspector }: AppHeaderProps) {
  const showInspector = Boolean(run) && page === "research";
  return (
    <header className="app-header">
      <div className="header-context">
        <button className="icon-button mobile-nav-button" type="button" aria-label="Open navigation" onClick={onOpenNav}>☰</button>
        <div>
          <p className="breadcrumb"><span>Meridian</span><span aria-hidden="true">/</span><strong>{pageTitles[page]}</strong></p>
          <p className="header-greeting">Good to see you, {session.name.split(" ")[0]}</p>
        </div>
      </div>
      <div className="header-actions">
        <div className="runtime-pill">
          <span className={`runtime-dot runtime-dot-${String(runtimeStatus).toLowerCase()}`} aria-hidden="true" />
          <span>{runtimeLabel(runtimeStatus)}</span>
          {health?.knowledge_base?.status && <small>{health.knowledge_base.status === "READY" ? "Corpus ready" : "Corpus needs attention"}</small>}
        </div>
        {showInspector && <button className="button button-secondary header-inspector-button" type="button" onClick={onOpenInspector}>Inspect run <span aria-hidden="true">↗</span></button>}
        <span className="header-local-label"><span aria-hidden="true">◉</span> Local only</span>
      </div>
    </header>
  );
}

function runtimeLabel(status: RunStatus | string) {
  switch (String(status).toUpperCase()) {
    case "CONNECTING": return "Connecting";
    case "RUNNING": return "Running locally";
    case "READY": return "Runtime ready";
    case "OFFLINE": return "Runtime unavailable";
    default: return "Status unknown";
  }
}
