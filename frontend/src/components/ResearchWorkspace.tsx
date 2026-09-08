import type { RunMetrics } from "../types/api";
import type { NormalizedUiRun } from "../lib/uiAdapter";
import { StatusBadge } from "./StatusBadge";
import { TaskGraph } from "./TaskGraph";

const flagRows = [
  ["P", "Planning retrieval", ["P", "planning_enabled", "p_enabled"]],
  ["N", "Task normalization", ["N", "normalization_enabled", "task_normalization_enabled", "n_enabled"]],
  ["O", "Overlap allocation", ["O", "overlap_enabled", "overlap_context_enabled", "o_enabled"]],
] as const;

function unique(values: string[]): string[] {
  return Array.from(new Set(values.filter(Boolean)));
}

function flagValue(flags: Record<string, boolean>, aliases: readonly string[]): { label: string; tone: string } {
  const key = aliases.find((alias) => Object.prototype.hasOwnProperty.call(flags, alias));
  if (!key) return { label: "Not recorded", tone: "muted" };
  return flags[key]
    ? { label: "Enabled", tone: "enabled" }
    : { label: "Disabled", tone: "disabled" };
}

function totalTokens(metrics: RunMetrics | null): number | null {
  if (!metrics) return null;
  if (typeof metrics.total_tokens === "number") return metrics.total_tokens;
  if (typeof metrics.input_tokens === "number" && typeof metrics.output_tokens === "number") {
    return metrics.input_tokens + metrics.output_tokens;
  }
  return null;
}

function metricValue(value: number | string | null | undefined, suffix = "") {
  if (value === null || value === undefined || value === "") return "—";
  const display = typeof value === "number" ? new Intl.NumberFormat().format(value) : value;
  return `${display}${suffix}`;
}

function stageLabel(stage: string | undefined): string {
  if (!stage) return "No stage recorded";
  const labels: Record<string, string> = {
    run_started: "Run started",
    vanilla_retrieval: "Retrieved candidate evidence",
    planning_retrieval: "Retrieved planning evidence",
    decomposition: "Recorded task plan",
    normalization: "Normalized task plan",
    task_retrieval: "Retrieved task evidence",
    task_completed: "Completed task",
    answer_generated: "Generated answer",
    run_finished: "Run finished",
    run_failed: "Run failed",
  };
  return labels[stage] ?? stage.replace(/[_-]+/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function ResearchFlagStrip({ run, compact = false }: { run: NormalizedUiRun; compact?: boolean }) {
  const flags = run.researchFlags.effectiveConfigFlags;
  return (
    <div className={`research-flag-strip${compact ? " research-flag-strip-compact" : ""}`} aria-label="P N O effective configuration">
      {flagRows.map(([letter, label, aliases]) => {
        const value = flagValue(flags, aliases);
        return (
          <div className="research-flag-item" key={letter}>
            <span className="research-flag-letter" aria-hidden="true">{letter}</span>
            <span className="research-flag-copy"><strong>{label}</strong><small>{value.label}</small></span>
            <span className={`research-flag-state research-flag-state-${value.tone}`}>{value.tone === "enabled" ? "On" : value.tone === "disabled" ? "Off" : "—"}</span>
          </div>
        );
      })}
    </div>
  );
}

function ResearchMetrics({ run, compact = false }: { run: NormalizedUiRun; compact?: boolean }) {
  const metrics = run.metrics;
  const entries = [
    ["Total tokens", metricValue(totalTokens(metrics))],
    ["Latency", metricValue(metrics?.latency_ms, " ms")],
    ["LLM calls", metricValue(metrics?.llm_calls)],
    ["Retrieved", metricValue(metrics?.retrieved_chunks)],
    ["Selected", metricValue(metrics?.selected_chunks)],
    ["Context est.", metricValue(metrics?.context_tokens_est, " tok")],
  ] as const;

  return (
    <div className={`research-metrics-grid${compact ? " research-metrics-grid-compact" : ""}`} aria-label="Research runtime metrics">
      {entries.map(([label, value]) => (
        <div className="research-metric" key={label}>
          <span>{label}</span>
          <strong>{value}</strong>
        </div>
      ))}
    </div>
  );
}

function LabelRoster({ run }: { run: NormalizedUiRun }) {
  const taskAgents = run.tasks.map((task) => task.agent ?? "");
  const taskRoles = run.tasks.map((task) => task.roleProfile ?? "");
  const agents = unique([...run.agents, ...taskAgents]);
  const roles = unique([...run.roles, ...taskRoles]);

  return (
    <section className="research-roster" aria-labelledby="research-roster-title">
      <div className="research-panel-heading">
        <div><span className="section-eyebrow">Explicit labels</span><h3 id="research-roster-title">Agents & roles</h3></div>
        <span>Run record only</span>
      </div>
      <div className="research-roster-columns">
        <div>
          <span className="research-roster-label">Agents</span>
          {agents.length > 0 ? <div className="research-chip-list">{agents.map((agent) => <code key={agent}>{agent}</code>)}</div> : <p>No agent labels recorded.</p>}
        </div>
        <div>
          <span className="research-roster-label">Roles</span>
          {roles.length > 0 ? <div className="research-chip-list">{roles.map((role) => <code key={role}>{role}</code>)}</div> : <p>No role labels recorded.</p>}
        </div>
      </div>
    </section>
  );
}

export function ResearchWorkspace({ run, onOpenResearch }: { run: NormalizedUiRun; onOpenResearch: () => void }) {
  const latestStage = run.traceSummary.stages.at(-1);
  const boundaryCopy = run.researchFlags.isWiringOnly
    ? "FakeProvider is a wiring/test double. This record is not semantic or milestone evidence."
    : `${run.researchFlags.evidenceBoundary.replace(/_/g, " ")} · Human correctness and faithfulness remain UNSCORED.`;

  return (
    <section className="research-workspace" aria-labelledby="research-workspace-title">
      <div className="research-workspace-heading">
        <div>
          <span className="section-eyebrow">Research / Demo view</span>
          <h2 id="research-workspace-title">Run anatomy</h2>
          <p>Trace the recorded task shape, effective P / N / O flags, and measured local runtime in one pass.</p>
        </div>
        <div className="research-workspace-actions">
          <span className="research-latest-stage"><span className="research-live-dot" aria-hidden="true" />{stageLabel(latestStage)}</span>
          <StatusBadge status={run.status} compact />
          <button className="secondary-action" type="button" onClick={onOpenResearch}>Open inspector <span aria-hidden="true">↗</span></button>
        </div>
      </div>

      <div className={`research-boundary-inline${run.researchFlags.isWiringOnly ? " research-boundary-inline-warning" : ""}`} role="note">
        <span className="research-boundary-icon" aria-hidden="true">{run.researchFlags.isWiringOnly ? "!" : "i"}</span>
        <span><strong>{run.researchFlags.isWiringOnly ? "Wiring boundary" : "Evidence boundary"}</strong>{boundaryCopy}</span>
      </div>

      <div className="research-overview-grid">
        <section className="research-panel" aria-labelledby="research-flags-heading">
          <div className="research-panel-heading"><div><span className="section-eyebrow">Configuration</span><h3 id="research-flags-heading">P / N / O</h3></div><span>Effective flags</span></div>
          <ResearchFlagStrip run={run} />
        </section>
        <section className="research-panel" aria-labelledby="research-metrics-heading">
          <div className="research-panel-heading"><div><span className="section-eyebrow">Measured runtime</span><h3 id="research-metrics-heading">Resource readout</h3></div><span>Quality not scored</span></div>
          <ResearchMetrics run={run} />
        </section>
      </div>

      <section className="research-panel research-graph-panel" aria-labelledby="research-graph-heading">
        <div className="research-panel-heading"><div><span className="section-eyebrow">Recorded topology</span><h3 id="research-graph-heading">Task dependency graph</h3></div><span>{run.tasks.length} {run.tasks.length === 1 ? "task" : "tasks"}</span></div>
        <TaskGraph tasks={run.tasks} />
      </section>

      <LabelRoster run={run} />
    </section>
  );
}
