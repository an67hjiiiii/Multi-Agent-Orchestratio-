import { useEffect, useRef, useState } from "react";
import type {
  PLiteInspectionResponse,
  RunEvent,
  SourceChunk,
  SourceSummary,
  KnowledgeBaseStatus,
} from "../types/api";
import type { SourceImportState } from "../app/useResearchApp";
import type { NormalizedUiRun, NormalizedUiTask } from "../lib/uiAdapter";
import { api } from "../lib/api";
import { PlanningEvidencePanel } from "./PlanningEvidencePanel";
import { KnowledgeWorkspace } from "./KnowledgeWorkspace";
import { ResearchFlagStrip } from "./ResearchWorkspace";
import { StatusBadge } from "./StatusBadge";
import { TaskResultPanel } from "./TaskResultPanel";
import { TaskGraph } from "./TaskGraph";
import type { ViewMode } from "./WorkspaceHeader";

export type DrawerTab = "context" | "evidence" | "sources" | "metrics" | "research" | "plan";

interface EvidenceDrawerProps {
  open: boolean;
  mode: ViewMode;
  activeTab: DrawerTab;
  onTabChange: (tab: DrawerTab) => void;
  onClose: () => void;
  run: NormalizedUiRun | null;
  sources: SourceSummary[];
  sourceSnapshotId: string | null;
  sourceImport: SourceImportState;
  isImporting: boolean;
  onImport: (file: File) => Promise<void>;
  focusCitationId: string | null;
  canInspectPlan: boolean;
  planningInspection: PLiteInspectionResponse | null;
  planningError: string | null;
  isInspectingPlan: boolean;
  onInspectPlan: () => void;
  knowledgeStatus?: KnowledgeBaseStatus | null;
  retrievalMode?: string | null;
}

function unique(values: string[]) {
  return Array.from(new Set(values.filter(Boolean)));
}

function formatValue(value: unknown, suffix = "") {
  if (value === null || value === undefined || value === "") return "—";
  const display = typeof value === "number" ? new Intl.NumberFormat().format(value) : String(value);
  return `${display}${suffix}`;
}

function formatTime(value?: string) {
  if (!value) return "Time not recorded";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Time not recorded";
  return new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit" }).format(date);
}

function stageLabel(stage: string) {
  const known: Record<string, string> = {
    run_started: "Run started",
    vanilla_retrieval: "Retrieved candidate evidence",
    task_created: "Task recorded",
    task_result: "Task result recorded",
    answer_generated: "Answer returned",
    run_finished: "Run finished",
    run_failed: "Run failed",
  };
  if (known[stage]) return known[stage];
  return stage.replace(/[_-]+/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function eventEvidenceIds(event: RunEvent) {
  return unique([...(event.selected ?? []), ...(event.candidates ?? [])]);
}

function DrawerEmpty({ title, copy }: { title: string; copy: string }) {
  return <div className="drawer-empty" role="status"><strong>{title}</strong><span>{copy}</span></div>;
}

function EvidenceContext({
  run,
  selectedChunk,
  selectedChunkId,
  loadingId,
  error,
  mode,
  onInspectChunk,
  onRetry,
}: {
  run: NormalizedUiRun | null;
  selectedChunk: SourceChunk | null;
  selectedChunkId: string | null;
  loadingId: string | null;
  error: string | null;
  mode: ViewMode;
  onInspectChunk: (chunkId: string) => void;
  onRetry: () => void;
}) {
  if (!run) return <DrawerEmpty title="No run selected" copy="Ask a question to open the evidence thread." />;

  const relatedTasks = selectedChunk
    ? run.tasks.filter((task) => [...task.citations, ...task.evidenceIds].includes(selectedChunk.chunk_id))
    : [];

  return (
    <div className="drawer-stack">
      <div className="drawer-section-intro">
        <span className="section-eyebrow">Evidence thread</span>
        <h3>Context for this answer</h3>
        <p>Source context leads; locator details stay available when you need to audit the run.</p>
      </div>

      {loadingId && (
        <div className="drawer-loading" role="status" aria-live="polite">
          <span className="drawer-loading-bar" aria-hidden="true" />
          <span>Loading source context…</span>
        </div>
      )}

      {error && (
        <div className="drawer-error" role="alert">
          <strong>Evidence could not be loaded</strong>
          <span>{error}</span>
          <button className="secondary-action" type="button" onClick={onRetry} disabled={!selectedChunkId || loadingId !== null}>Try again</button>
          {mode === "research" && selectedChunkId && <details><summary>Technical locator</summary><code>{selectedChunkId}</code></details>}
        </div>
      )}

      {selectedChunk ? (
        <article className="context-card">
          <div className="context-card-topline">
            <span className="evidence-valid-label"><span aria-hidden="true">✓</span> Validated citation</span>
            <StatusBadge status="COMPLETE" compact />
          </div>
          <h4>{selectedChunk.source_name || "Source context"}</h4>
          <p className="context-location">Chunk {selectedChunk.index + 1} · {selectedChunk.chunk_id}</p>
          <div className="context-excerpt"><p>{selectedChunk.text}</p></div>
          <p className="context-disclaimer">The API does not return claim offsets, so no text highlight is inferred here.</p>
          {relatedTasks.length > 0 && (
            <div className="context-related">
              <span className="drawer-label">Related task{relatedTasks.length === 1 ? "" : "s"}</span>
              {relatedTasks.map((task) => <TaskAssociation key={task.taskId} task={task} />)}
            </div>
          )}
          {mode === "research" && (
            <details className="technical-details">
              <summary>Technical details</summary>
              <dl>
                <div><dt>Canonical locator</dt><dd><code>{selectedChunk.chunk_id}</code></dd></div>
                <div><dt>Source ID</dt><dd><code>{selectedChunk.source_id}</code></dd></div>
                {selectedChunk.score !== undefined && <div><dt>Retrieved score</dt><dd>{formatValue(selectedChunk.score)}</dd></div>}
              </dl>
            </details>
          )}
        </article>
      ) : (
        <div className="context-link-list">
          <span className="drawer-label">Validated citations from this run</span>
          {run.citations.length === 0 ? (
            <DrawerEmpty title="No validated citations" copy="This run did not return a source locator to inspect." />
          ) : (
            run.citations.map((citation, index) => (
              <button className="drawer-citation-button" type="button" key={citation} onClick={() => onInspectChunk(citation)} disabled={loadingId !== null}>
                <span className="citation-index" aria-hidden="true">{String(index + 1).padStart(2, "0")}</span>
                <span><strong>Open source context</strong><small>{citation}</small></span>
                <span aria-hidden="true">↗</span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}

function TaskAssociation({ task }: { task: NormalizedUiTask }) {
  return (
    <div className="task-association">
      <strong>{task.taskId}</strong>
      <span>{task.goal ?? "Task goal not recorded"}</span>
    </div>
  );
}

function TraceEvent({ event, index, onInspectChunk }: { event: RunEvent; index: number; onInspectChunk: (id: string) => void }) {
  const selected = unique(event.selected ?? []);
  const dropped = unique((event.dropped ?? []).map((item) => item.chunk_id ?? ""));
  const ids = eventEvidenceIds(event);

  return (
    <li className="trace-item">
      <span className="trace-marker" aria-hidden="true">{String(index + 1).padStart(2, "0")}</span>
      <div className="trace-line" aria-hidden="true" />
      <div className="trace-copy">
        <div className="trace-heading"><strong>{stageLabel(event.stage)}</strong><time>{formatTime(event.ts)}</time></div>
        {event.task_id && <span className="trace-task">Task {event.task_id}</span>}
        <p>
          {selected.length > 0 ? `${selected.length} selected` : "No selected evidence"}
          {event.candidates?.length ? ` · ${event.candidates.length} candidates` : ""}
          {event.dropped?.length ? ` · ${event.dropped.length} dropped` : ""}
        </p>
        {ids.length > 0 && (
          <div className="trace-id-list">
            {ids.map((id) => <button className="trace-id-button" type="button" key={id} onClick={() => onInspectChunk(id)}>{id}</button>)}
          </div>
        )}
        {dropped.length > 0 && (
          <details className="trace-dropped"><summary>Why evidence was dropped</summary><ul>{event.dropped?.map((item, dropIndex) => <li key={`${item.chunk_id ?? "dropped"}-${dropIndex}`}><code>{item.chunk_id ?? "locator not recorded"}</code> · {item.reason ?? "Reason not recorded"}{item.estimated_tokens === undefined ? "" : ` · ${item.estimated_tokens} tokens`}</li>)}</ul></details>
        )}
      </div>
    </li>
  );
}

function EvidenceTrail({ run, onInspectChunk }: { run: NormalizedUiRun | null; onInspectChunk: (id: string) => void }) {
  if (!run) return <DrawerEmpty title="No run selected" copy="Retrieval events appear after a question resolves." />;
  const events = run.traceSummary.events;
  const results = run.tasks;

  return (
    <div className="drawer-stack">
      <div className="drawer-section-intro"><span className="section-eyebrow">Returned trace</span><h3>Evidence trail</h3><p>Only stages present in the run record are shown. A planning ID is never treated as answer evidence.</p></div>
      {events.length === 0 ? <DrawerEmpty title="No trace events returned" copy="This run did not include a retrieval timeline." /> : <ol className="trace-timeline" aria-label="Evidence trace timeline">{events.map((event, index) => <TraceEvent event={event} index={index} key={`${event.stage}-${event.task_id ?? "run"}-${index}`} onInspectChunk={onInspectChunk} />)}</ol>}
      {results.length > 0 && (
        <section className="audit-summary" aria-labelledby="audit-summary-title">
          <div className="drawer-card-heading"><h4 id="audit-summary-title">Citation audit</h4><span>{run.citations.length} valid · {run.invalidCitations.length} invalid</span></div>
          {results.map((task) => (
            <div className="audit-task" key={task.taskId}>
              <div><strong>{task.taskId}</strong><span>{task.domain ?? "Domain not recorded"}</span></div>
              <span>{task.citations.length} valid · {task.invalidCitations.length} invalid</span>
              {task.invalidCitations.length > 0 && <div className="invalid-citation-list">{task.invalidCitations.map((id) => <code key={id}>{id}</code>)}</div>}
            </div>
          ))}
        </section>
      )}
    </div>
  );
}

function MetricsPanel({ run }: { run: NormalizedUiRun | null }) {
  if (!run) return <DrawerEmpty title="No metrics yet" copy="Measured runtime values appear after a run." />;
  const metrics = run.metrics;
  const totalTokens = typeof metrics?.total_tokens === "number"
    ? metrics.total_tokens
    : typeof metrics?.input_tokens === "number" && typeof metrics.output_tokens === "number"
      ? metrics.input_tokens + metrics.output_tokens
      : undefined;
  const entries: Array<[string, string]> = [
    ["Total latency", formatValue(metrics?.latency_ms, " ms")],
    ["Retrieval latency", formatValue(metrics?.retrieval_latency_ms, " ms")],
    ["Generation latency", formatValue(metrics?.generation_latency_ms, " ms")],
    ["LLM calls", formatValue(metrics?.llm_calls)],
    ["Total tokens", formatValue(totalTokens)],
    ["Input tokens", formatValue(metrics?.input_tokens)],
    ["Output tokens", formatValue(metrics?.output_tokens)],
    ["Retrieved chunks", formatValue(metrics?.retrieved_chunks)],
    ["Selected chunks", formatValue(metrics?.selected_chunks)],
    ["Dropped chunks", formatValue(metrics?.dropped_chunks)],
    ["Context estimate", formatValue(metrics?.context_tokens_est, " tok")],
    ["Valid citations", formatValue(metrics?.citations_valid)],
    ["Citation validity", metrics?.citation_locator_validity === null || metrics?.citation_locator_validity === undefined ? "—" : `${Math.round(metrics.citation_locator_validity * 100)}%`],
  ];

  return (
    <div className="drawer-stack">
      <div className="drawer-section-intro"><span className="section-eyebrow">Measured runtime</span><h3>Run metrics</h3><p>Unavailable values remain explicit. These are measurements, not answer-quality scores.</p></div>
      <div className="metric-detail-grid">{entries.map(([label, value]) => <div className="metric-detail" key={label}><span>{label}</span><strong>{value}</strong></div>)}</div>
      <dl className="run-identity-details">
        <div><dt>Status</dt><dd><StatusBadge status={run.status} compact /></dd></div>
        <div><dt>Run ID</dt><dd><code>{run.runId}</code></dd></div>
        <div><dt>Snapshot</dt><dd><code>{run.raw.source_snapshot_id ?? "Not recorded"}</code></dd></div>
        <div><dt>Config hash</dt><dd><code>{run.raw.config_hash ?? "Not recorded"}</code></dd></div>
        <div><dt>Provider</dt><dd>{run.raw.provider ?? "Not recorded"}</dd></div>
        <div><dt>Model</dt><dd>{run.raw.model ?? "Not recorded"}</dd></div>
      </dl>
    </div>
  );
}

function ResearchPanel({ run, onInspectChunk }: { run: NormalizedUiRun | null; onInspectChunk: (id: string) => void }) {
  if (!run) return <DrawerEmpty title="No research details" copy="Run details appear after a question resolves." />;

  return (
    <div className="drawer-stack">
      <div className="drawer-section-intro"><span className="section-eyebrow">Research / Demo</span><h3>Explain this run</h3><p>Returned execution detail is separated from human review and milestone approval.</p></div>
      <div className={`research-boundary research-boundary-${run.researchFlags.evidenceBoundary.toLowerCase()}`} role="note">
        <strong>{run.researchFlags.isWiringOnly ? "Wiring/test boundary" : "Evidence boundary"}</strong>
        <span>{run.researchFlags.isWiringOnly ? "FakeProvider is a test double. This run is not semantic or milestone evidence." : `${run.researchFlags.evidenceBoundary.replace(/_/g, " ")} · human review remains separate.`}</span>
      </div>
      <section className="research-section" aria-labelledby="research-flags-title">
        <div className="drawer-card-heading"><h4 id="research-flags-title">P / N / O flags</h4><span>Effective config</span></div>
        <ResearchFlagStrip run={run} compact />
      </section>
      <section className="research-section" aria-labelledby="research-tasks-title">
        <div className="drawer-card-heading"><h4 id="research-tasks-title">Recorded tasks</h4><span>{run.tasks.length}</span></div>
        <TaskGraph tasks={run.tasks} compact />
      </section>
      {(run.agents.length > 0 || run.roles.length > 0) && (
        <section className="research-section" aria-labelledby="research-labels-title">
          <div className="drawer-card-heading"><h4 id="research-labels-title">Recorded labels</h4><span>Only explicit fields</span></div>
          {run.agents.length > 0 && <div className="research-label-row"><span>Agents</span><div>{run.agents.map((agent) => <code key={agent}>{agent}</code>)}</div></div>}
          {run.roles.length > 0 && <div className="research-label-row"><span>Roles</span><div>{run.roles.map((role) => <code key={role}>{role}</code>)}</div></div>}
        </section>
      )}
      <section className="research-section" aria-labelledby="research-trace-title">
        <div className="drawer-card-heading"><h4 id="research-trace-title">Human-readable trace</h4><span>{run.traceSummary.eventCount} event{run.traceSummary.eventCount === 1 ? "" : "s"}</span></div>
        {run.traceSummary.events.length === 0 ? <p className="drawer-muted">No trace events were returned.</p> : <ol className="trace-timeline trace-timeline-compact">{run.traceSummary.events.map((event, index) => <TraceEvent event={event} index={index} key={`${event.stage}-${index}`} onInspectChunk={onInspectChunk} />)}</ol>}
      </section>
      <section className="research-review-state" aria-label="Human review boundary"><span>Human correctness</span><strong>{run.researchFlags.manualCorrectness}</strong><span>Human faithfulness</span><strong>{run.researchFlags.manualFaithfulness}</strong><span>Milestone evidence</span><strong>No</strong></section>
    </div>
  );
}

function PlanPanel({ result, error, isLoading }: { result: PLiteInspectionResponse | null; error: string | null; isLoading: boolean }) {
  const planning = result?.planning ?? (result ? { request: result.request, item_ids: result.planning_evidence_ids, scores: null, context: result.planning_context ?? null } : null);
  return (
    <div className="drawer-stack" aria-busy={isLoading}>
      <div className="drawer-section-intro"><span className="section-eyebrow">Planning only</span><h3>P-lite task plan</h3><p>This inspection is separate from answer-domain citations and never implies spawned agents.</p></div>
      {isLoading && <div className="drawer-loading" role="status"><span className="drawer-loading-bar" aria-hidden="true" />Inspecting bounded planning guidance…</div>}
      <PlanningEvidencePanel result={planning} />
      <TaskResultPanel result={result} error={error} />
    </div>
  );
}

export function EvidenceDrawer({
  open,
  mode,
  activeTab,
  onTabChange,
  onClose,
  run,
  sources,
  sourceSnapshotId,
  sourceImport,
  isImporting,
  onImport,
  focusCitationId,
  canInspectPlan,
  planningInspection,
  planningError,
  isInspectingPlan,
  onInspectPlan,
  knowledgeStatus,
  retrievalMode,
}: EvidenceDrawerProps) {
  const drawerRef = useRef<HTMLElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const [selectedChunk, setSelectedChunk] = useState<SourceChunk | null>(null);
  const [selectedChunkId, setSelectedChunkId] = useState<string | null>(null);
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [chunkError, setChunkError] = useState<string | null>(null);

  async function inspectChunk(chunkId: string) {
    setSelectedChunkId(chunkId);
    setLoadingId(chunkId);
    setChunkError(null);
    try {
      setSelectedChunk(await api.getChunk(chunkId));
      onTabChange("context");
    } catch (cause) {
      setSelectedChunk(null);
      setChunkError(cause instanceof Error ? cause.message : "Unable to load evidence context");
    } finally {
      setLoadingId(null);
    }
  }

  useEffect(() => {
    if (open && focusCitationId) void inspectChunk(focusCitationId);
    // The drawer intentionally reacts to a citation request, not every run update.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, focusCitationId]);

  useEffect(() => {
    if (!open) return;
    const drawer = drawerRef.current;
    closeRef.current?.focus();

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== "Tab" || !drawer) return;

      const focusable = Array.from(
        drawer.querySelectorAll<HTMLElement>(
          'button:not([disabled]), select:not([disabled]), textarea:not([disabled]), input:not([disabled]), [href], [tabindex]:not([tabindex="-1"])',
        ),
      );
      if (focusable.length === 0) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  const tabs: Array<{ id: DrawerTab; label: string }> = [
    { id: "context", label: "Context" },
    { id: "evidence", label: "Evidence trail" },
    { id: "sources", label: "Sources" },
    { id: "research", label: "Research" },
    ...(mode === "research" ? [{ id: "metrics" as const, label: "Metrics" }] : []),
    ...(canInspectPlan ? [{ id: "plan" as const, label: "Plan" }] : []),
  ];

  const safeTab = tabs.some((tab) => tab.id === activeTab) ? activeTab : "context";

  return (
    <div className="drawer-layer">
      <button className="drawer-backdrop" type="button" aria-label="Close evidence drawer" onClick={onClose} />
      <aside ref={drawerRef} className="evidence-drawer" role="dialog" aria-modal="true" aria-labelledby="evidence-drawer-title">
        <div className="drawer-header">
          <div><span className="section-eyebrow">Inspector</span><h2 id="evidence-drawer-title">{run ? "Evidence & run details" : "Evidence inspector"}</h2><p>{run ? `Run ${run.runId.slice(-8)}` : "No active run"}</p></div>
          <div className="drawer-header-actions"><button ref={closeRef} className="icon-button" type="button" aria-label="Close evidence drawer" onClick={onClose}>×</button>{run && <StatusBadge status={run.status} compact />}</div>
        </div>
        <div className="drawer-tabs" role="tablist" aria-label="Evidence inspector sections">
          {tabs.map((tab) => (
            <button
              className={safeTab === tab.id ? "drawer-tab drawer-tab-active" : "drawer-tab"}
              type="button"
              role="tab"
              aria-selected={safeTab === tab.id}
              aria-controls={`drawer-panel-${tab.id}`}
              id={`drawer-tab-${tab.id}`}
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <div className="drawer-content">
          {safeTab === "context" && <div id="drawer-panel-context" role="tabpanel" aria-labelledby="drawer-tab-context"><EvidenceContext run={run} selectedChunk={selectedChunk} selectedChunkId={selectedChunkId} loadingId={loadingId} error={chunkError} mode={mode} onInspectChunk={(id) => void inspectChunk(id)} onRetry={() => { if (selectedChunkId) void inspectChunk(selectedChunkId); }} /></div>}
          {safeTab === "evidence" && <div id="drawer-panel-evidence" role="tabpanel" aria-labelledby="drawer-tab-evidence"><EvidenceTrail run={run} onInspectChunk={(id) => void inspectChunk(id)} /></div>}
          {safeTab === "sources" && <div id="drawer-panel-sources" role="tabpanel" aria-labelledby="drawer-tab-sources"><KnowledgeWorkspace sources={sources} sourceSnapshotId={sourceSnapshotId} sourceImport={sourceImport} isImporting={isImporting} onImport={onImport} onInspectChunk={(id) => void inspectChunk(id)} knowledgeStatus={knowledgeStatus} retrievalMode={retrievalMode} researchMode={mode === "research"} /></div>}
          {safeTab === "research" && <div id="drawer-panel-research" role="tabpanel" aria-labelledby="drawer-tab-research"><ResearchPanel run={run} onInspectChunk={(id) => void inspectChunk(id)} /></div>}
          {safeTab === "metrics" && <div id="drawer-panel-metrics" role="tabpanel" aria-labelledby="drawer-tab-metrics"><MetricsPanel run={run} /></div>}
          {safeTab === "plan" && canInspectPlan && <div id="drawer-panel-plan" role="tabpanel" aria-labelledby="drawer-tab-plan"><PlanPanel result={planningInspection} error={planningError} isLoading={isInspectingPlan} /></div>}
        </div>
        {canInspectPlan && run?.raw.query && <div className="drawer-footer"><button className="inline-action" type="button" onClick={onInspectPlan} disabled={isInspectingPlan}>{isInspectingPlan ? "Inspecting plan…" : planningInspection ? "Refresh plan" : "Inspect P-lite plan"}</button></div>}
      </aside>
    </div>
  );
}
