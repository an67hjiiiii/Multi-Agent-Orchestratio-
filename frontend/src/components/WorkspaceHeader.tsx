import type { HealthResponse, RunStatus } from "../types/api";
import type { NormalizedUiRun } from "../lib/uiAdapter";
import { StatusBadge } from "./StatusBadge";

export type ViewMode = "normal" | "research";

interface WorkspaceHeaderProps {
  mode: ViewMode;
  onModeChange: (mode: ViewMode) => void;
  runtimeStatus: RunStatus;
  health: HealthResponse | null;
  run: NormalizedUiRun | null;
  sourceCount: number;
  onOpenRail: (trigger?: HTMLButtonElement) => void;
  onOpenResearch: () => void;
}
function runtimeCopy(status: RunStatus) {
  switch (String(status).toUpperCase()) {
    case "CONNECTING":
      return "Connecting to local runtime";
    case "RUNNING":
      return "Local run in progress";
    case "READY":
      return "Local runtime ready";
    case "OFFLINE":
      return "Local runtime unavailable";
    default:
      return "Local runtime status unknown";
  }
}

function providerLabel(run: NormalizedUiRun | null) {
  const provider = run?.raw.provider ?? "not selected";
  return provider.toLowerCase() === "fake" ? "Fake · wiring/test only" : provider;
}

export function WorkspaceHeader({
  mode,
  onModeChange,
  runtimeStatus,
  health,
  run,
  sourceCount,
  onOpenRail,
  onOpenResearch,
}: WorkspaceHeaderProps) {
  const profile = run?.raw.implementation_profile ?? health?.implementation_profile;
  const condition = run?.condition ?? health?.allowed_conditions?.[0] ?? "A";

  return (
    <header className="workspace-header">
      <div className="header-leading">
        <button
          className="mobile-rail-button"
          type="button"
          aria-label="Open workspace navigation"
          onClick={(event) => onOpenRail(event.currentTarget)}
        >
          <span aria-hidden="true">☰</span>
        </button>
        <div className="workspace-identity">
          <span className="workspace-kicker">LOCAL EVIDENCE DESK</span>
          <div className="workspace-name-row">
            <h1>Local Multi-Agent RAG</h1>
            <span className="workspace-source-count">
              {sourceCount} {sourceCount === 1 ? "source" : "sources"}
            </span>
          </div>
        </div>
      </div>

      <div className="header-actions">
        <div className="mode-switch" role="group" aria-label="Presentation mode">
          <button
            className={mode === "normal" ? "mode-button mode-button-active" : "mode-button"}
            type="button"
            aria-pressed={mode === "normal"}
            onClick={() => onModeChange("normal")}
          >
            Normal
          </button>
          <button
            className={mode === "research" ? "mode-button mode-button-active" : "mode-button"}
            type="button"
            aria-pressed={mode === "research"}
            onClick={() => onModeChange("research")}
          >
            Research / Demo
          </button>
        </div>

        <div className="runtime-indicator">
          <StatusBadge status={runtimeStatus} compact />
          <span className="runtime-copy">{runtimeCopy(runtimeStatus)}</span>
        </div>

        {mode === "research" && (
          <div className="header-research-context" aria-label="Research run context">
            <span>Condition <strong>{condition}</strong></span>
            <span>{profile ?? "profile not recorded"}</span>
            <span>{providerLabel(run)}</span>
            {run?.raw.model && <span>{run.raw.model}</span>}
          </div>
        )}

        {mode === "normal" && run?.researchFlags.isWiringOnly && (
          <span className="header-boundary-note">Wiring/test only</span>
        )}

        <button
          className="header-inspect-button"
          type="button"
          onClick={onOpenResearch}
          disabled={!run}
        >
          {mode === "research" ? "Inspect run" : "Inspect"}
        </button>
      </div>
    </header>
  );
}
