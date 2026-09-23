import type { WorkspaceReadiness } from "../features/workspace/readiness";

interface WorkspaceReadinessBannerProps {
  status: WorkspaceReadiness;
  detail: string;
  retrying: boolean;
  onRetry: () => void;
}

export function WorkspaceReadinessBanner({ status, detail, retrying, onRetry }: WorkspaceReadinessBannerProps) {
  const canRetry = status === "OFFLINE" || status === "DEGRADED";
  const label = status === "READY_EMPTY" ? "Ready · empty corpus" : status[0] + status.slice(1).toLowerCase();
  return (
    <section className={`readiness-banner readiness-banner-${status.toLowerCase()}`} aria-label="Workspace readiness" role="status" aria-live="polite">
      <span className="readiness-mark" aria-hidden="true">{status === "READY" || status === "READY_EMPTY" ? "✓" : status === "BOOTING" ? "…" : "!"}</span>
      <div className="readiness-copy"><strong>{label}</strong><span>{detail}</span></div>
      {canRetry && <button className="button button-quiet readiness-retry" type="button" onClick={onRetry} disabled={retrying}>{retrying ? "Checking locally…" : "Retry bootstrap"}</button>}
    </section>
  );
}
