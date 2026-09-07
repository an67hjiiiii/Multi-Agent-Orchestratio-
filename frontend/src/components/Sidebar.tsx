import { useMemo, useState } from "react";
import type { RunListItem, SourceSummary } from "../types/api";
import type { ViewMode } from "./WorkspaceHeader";
import { StatusBadge } from "./StatusBadge";

interface SidebarProps {
  history: RunListItem[];
  sources: SourceSummary[];
  activeRunId?: string;
  isOpen?: boolean;
  onClose?: () => void;
  onNewRun: () => void;
  onSelectRun: (runId: string) => void;
  mode: ViewMode;
  onModeToggle: () => void;
  provider: string;
  onProviderChange: (provider: string) => void;
  onOpenSources: () => void;
}
function formatDate(value?: string) {
  if (!value) return "Unknown time";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown time";
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(date);
}

function corpusDescription(sources: SourceSummary[]) {
  if (sources.length === 0) return "Add a source to begin";
  const chunkCount = sources.reduce((total, source) => total + source.chunk_count, 0);
  return `${chunkCount} ${chunkCount === 1 ? "chunk" : "chunks"} across ${sources.length} ${sources.length === 1 ? "source" : "sources"}`;
}

export function Sidebar({
  history,
  sources,
  activeRunId,
  isOpen = true,
  onClose = () => undefined,
  onNewRun,
  onSelectRun,
  mode,
  onModeToggle,
  provider,
  onProviderChange,
  onOpenSources,
}: SidebarProps) {
  const [searchOpen, setSearchOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(true);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [search, setSearch] = useState("");

  const filteredHistory = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return history;
    return history.filter((item) =>
      [item.query, item.condition, item.status, item.run_id]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(query)),
    );
  }, [history, search]);

  function chooseRun(runId: string) {
    onSelectRun(runId);
    onClose();
  }

  function createRun() {
    onNewRun();
    onClose();
  }

  return (
    <>
      {isOpen && <button className="rail-backdrop" type="button" aria-label="Close workspace navigation" onClick={onClose} />}
      <aside className={`context-rail${isOpen ? " context-rail-open" : ""}`} aria-label="Workspace navigation">
        <div className="rail-brand-row">
          <div className="rail-brand">
            <span className="rail-brand-mark" aria-hidden="true">LE</span>
            <span>
              <strong>Evidence desk</strong>
              <small>Local research workspace</small>
            </span>
          </div>
          <button className="rail-close-button" type="button" aria-label="Close workspace navigation" onClick={onClose}>
            ×
          </button>
        </div>

        <button className="rail-primary-action" type="button" onClick={createRun}>
          <span className="rail-primary-icon" aria-hidden="true">＋</span>
          <span>New question</span>
          <span className="rail-shortcut" aria-hidden="true">N</span>
        </button>

        <nav className="rail-nav" aria-label="Workspace tools">
          <button
            className={historyOpen ? "rail-nav-button rail-nav-button-active" : "rail-nav-button"}
            type="button"
            aria-pressed={historyOpen}
            onClick={() => setHistoryOpen((open) => !open)}
          >
            <span className="rail-nav-icon" aria-hidden="true">↺</span>
            <span>History</span>
            <span className="rail-count">{history.length}</span>
          </button>
          <button
            className={searchOpen ? "rail-nav-button rail-nav-button-active" : "rail-nav-button"}
            type="button"
            aria-pressed={searchOpen}
            onClick={() => setSearchOpen((open) => !open)}
          >
            <span className="rail-nav-icon" aria-hidden="true">⌕</span>
            <span>Search</span>
          </button>
          <button className="rail-nav-button" type="button" onClick={onModeToggle}>
            <span className="rail-nav-icon" aria-hidden="true">◌</span>
            <span>{mode === "normal" ? "Research mode" : "Normal mode"}</span>
          </button>
          <button
            className={settingsOpen ? "rail-nav-button rail-nav-button-active" : "rail-nav-button"}
            type="button"
            aria-pressed={settingsOpen}
            onClick={() => setSettingsOpen((open) => !open)}
          >
            <span className="rail-nav-icon" aria-hidden="true">⚙</span>
            <span>Settings</span>
          </button>
        </nav>

        {searchOpen && (
          <div className="rail-search-wrap">
            <label htmlFor="history-search">Search saved questions</label>
            <div className="rail-search-control">
              <span aria-hidden="true">⌕</span>
              <input
                id="history-search"
                type="search"
                value={search}
                placeholder="Find a question…"
                onChange={(event) => setSearch(event.target.value)}
              />
              {search && (
                <button type="button" aria-label="Clear history search" onClick={() => setSearch("")}>
                  ×
                </button>
              )}
            </div>
          </div>
        )}

        {settingsOpen && (
          <section className="rail-settings" aria-label="Workspace settings">
            <div className="rail-section-eyebrow">Workspace boundaries</div>
            <p>Presentation mode changes what is shown, not the research condition or provider.</p>
            <div className="rail-setting-row"><span>Condition</span><code>A · locked in M0</code></div>
            <label className="rail-setting-select">
              <span>Run provider</span>
              <select value={provider} onChange={(event) => onProviderChange(event.target.value)}>
                <option value="fake">Fake · wiring/test only</option>
                <option value="ollama">Local Ollama</option>
              </select>
            </label>
          </section>
        )}

        <div className="rail-history-section">
          <div className="rail-section-heading">
            <span>Recent questions</span>
            <span>{filteredHistory.length}</span>
          </div>
          {!historyOpen ? (
            <p className="rail-collapsed-note">History is collapsed.</p>
          ) : filteredHistory.length === 0 ? (
            <p className="rail-empty">{search ? "No saved question matches that search." : "Completed questions will appear here."}</p>
          ) : (
            <div className="rail-history-list" aria-live="polite">
              {filteredHistory.map((item) => (
                <button
                  className={`rail-history-item${item.run_id === activeRunId ? " rail-history-item-active" : ""}`}
                  key={item.run_id}
                  type="button"
                  aria-current={item.run_id === activeRunId ? "page" : undefined}
                  onClick={() => chooseRun(item.run_id)}
                >
                  <span className="rail-history-meta">
                    <span>{formatDate(item.created_at)}</span>
                    <StatusBadge compact status={item.status} />
                  </span>
                  <strong>{item.query || "Untitled question"}</strong>
                  <small>{item.condition ? `Condition ${item.condition}` : "Condition not recorded"}</small>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="rail-footer">
          <button className="rail-corpus-card" type="button" onClick={onOpenSources}>
            <span className="rail-corpus-icon" aria-hidden="true">▤</span>
            <span>
              <strong>Corpus</strong>
              <small>{corpusDescription(sources)}</small>
            </span>
            <span className="rail-arrow" aria-hidden="true">→</span>
          </button>
          <div className="rail-local-label"><span className="rail-local-dot" aria-hidden="true" />Data stays on this machine</div>
        </div>
      </aside>
    </>
  );
}
