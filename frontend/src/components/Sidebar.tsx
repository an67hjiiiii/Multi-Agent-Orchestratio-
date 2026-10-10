import type { RunListItem, SourceSummary } from "../types/api";
import { StatusBadge } from "./StatusBadge";

interface SidebarProps {
  history: RunListItem[];
  sources: SourceSummary[];
  activeRunId?: string;
  onNewRun: () => void;
  onSelectRun: (runId: string) => void;
}
function formatDate(value?: string) {
  if (!value) return "Unknown time";
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(
    new Date(value),
  );
}

export function Sidebar({ history, sources, activeRunId, onNewRun, onSelectRun }: SidebarProps) {
  return (
    <aside className="sidebar" aria-label="Research workspace navigation">
      <div className="brand-lockup">
        <div className="brand-mark" aria-hidden="true">LR</div>
        <div>
          <div className="brand-name">Local RAG Lab</div>
          <div className="brand-subtitle">Research workspace</div>
        </div>
      </div>

      <button className="new-run-button" type="button" onClick={onNewRun}>
        <span aria-hidden="true">＋</span>
        New research run
      </button>

      <div className="sidebar-section-heading">
        <span>Run history</span>
        <span className="section-count">{history.length}</span>
      </div>
      <div className="run-history" aria-live="polite">
        {history.length === 0 ? (
          <p className="sidebar-empty">Your completed runs will appear here.</p>
        ) : (
          history.map((item) => (
            <button
              className={`history-item${item.run_id === activeRunId ? " history-item-active" : ""}`}
              key={item.run_id}
              type="button"
              onClick={() => onSelectRun(item.run_id)}
            >
              <span className="history-item-topline">
                <span className="history-condition">{item.condition ?? "—"}</span>
                <StatusBadge compact status={item.status} />
              </span>
              <span className="history-query">{item.query || "Untitled research run"}</span>
              <span className="history-date">{formatDate(item.created_at)}</span>
            </button>
          ))
        )}
      </div>

      <div className="sidebar-footer">
        <div className="corpus-summary">
          <span className="summary-icon" aria-hidden="true">⌁</span>
          <span>
            <strong>{sources.length} sources</strong>
            <small>Current corpus</small>
          </span>
        </div>
        <div className="local-only-label">
          <span className="status-dot" aria-hidden="true" />
          Local-only build
        </div>
      </div>
    </aside>
  );
}
