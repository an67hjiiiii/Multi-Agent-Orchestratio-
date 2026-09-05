import { useState } from "react";
import type { InspectorTab } from "../app/useResearchApp";
import type { RunRecord, SourceChunk, SourceSummary } from "../types/api";
import { api } from "../lib/api";
import { StatusBadge } from "./StatusBadge";

interface InspectorProps {
  run: RunRecord | null;
  sources: SourceSummary[];
  activeTab: InspectorTab;
  onTabChange: (tab: InspectorTab) => void;
}
const tabs: Array<{ id: InspectorTab; label: string }> = [
  { id: "evidence", label: "Evidence" },
  { id: "sources", label: "Sources" },
  { id: "metrics", label: "Metrics" },
];

function formatValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "number") return new Intl.NumberFormat().format(value);
  return String(value);
}

function EvidencePanel({ run }: { run: RunRecord | null }) {
  const events = (run?.events ?? []).filter((event) => event.selected || event.dropped);
  if (!run) return <EmptyPanel title="No run selected" copy="Evidence will appear after your first run." />;
  if (events.length === 0) return <EmptyPanel title="No evidence trace" copy="This run did not return retrieval events." />;

  return (
    <div className="inspector-list">
      {events.map((event, index) => (
        <div className="evidence-card" key={`${event.stage}-${event.task_id ?? index}`}>
          <div className="evidence-card-heading">
            <span>{event.task_id ?? "Run retrieval"}</span>
            <span className="evidence-stage">{event.stage}</span>
          </div>
          <div className="evidence-row">
            <span>Selected</span>
            <strong>{event.selected?.length ?? 0}</strong>
          </div>
          {event.selected?.map((chunk) => <code className="evidence-id" key={chunk}>{chunk}</code>)}
          <div className="evidence-row evidence-row-muted">
            <span>Dropped</span>
            <strong>{event.dropped?.length ?? 0}</strong>
          </div>
        </div>
      ))}
    </div>
  );
}

function SourcesPanel({ sources }: { sources: SourceSummary[] }) {
  const [selectedChunk, setSelectedChunk] = useState<SourceChunk | null>(null);
  const [loadingId, setLoadingId] = useState<string | null>(null);

  async function inspectSource(source: SourceSummary) {
    setLoadingId(source.source_id);
    try {
      // TODO(M0): source detail is not exposed as a stable UI contract yet; inspect the first chunk when available.
      const detail = await api.getChunk(`${source.source_id}_c0000`);
      setSelectedChunk(detail);
    } catch {
      setSelectedChunk(null);
    } finally {
      setLoadingId(null);
    }
  }

  if (sources.length === 0) return <EmptyPanel title="Corpus is empty" copy="Add a UTF-8 text or code file to begin." />;

  return (
    <div className="inspector-list">
      {sources.map((source) => (
        <div className="source-card" key={source.source_id}>
          <div className="source-card-heading">
            <span className="source-file-icon" aria-hidden="true">TXT</span>
            <span className="source-name">{source.source_name}</span>
          </div>
          <div className="source-card-meta">{source.chunk_count} chunks · {source.source_id}</div>
          <button className="text-button" type="button" onClick={() => void inspectSource(source)} disabled={loadingId === source.source_id}>
            {loadingId === source.source_id ? "Loading…" : "Inspect first chunk"}
          </button>
        </div>
      ))}
      {selectedChunk && (
        <div className="chunk-preview">
          <div className="chunk-preview-heading">
            <span>{selectedChunk.chunk_id}</span>
            <button type="button" className="close-preview" aria-label="Close source preview" onClick={() => setSelectedChunk(null)}>×</button>
          </div>
          <pre>{selectedChunk.text}</pre>
        </div>
      )}
    </div>
  );
}

function MetricsPanel({ run }: { run: RunRecord | null }) {
  const metrics = run?.metrics;
  const entries = metrics
    ? [
        ["Total latency", metrics.latency_ms === undefined ? undefined : `${formatValue(metrics.latency_ms)} ms`],
        ["LLM calls", metrics.llm_calls],
        ["Total tokens", metrics.total_tokens],
        ["Selected chunks", metrics.selected_chunks],
        ["Valid citations", metrics.citations_valid],
        ["Citation validity", metrics.citation_locator_validity === null || metrics.citation_locator_validity === undefined ? undefined : `${Math.round(metrics.citation_locator_validity * 100)}%`],
      ]
    : [];

  if (!run) return <EmptyPanel title="No metrics yet" copy="Runtime measurements will appear after a run." />;
  return (
    <div className="metric-list">
      {entries.map(([label, value]) => (
        <div className="metric-row" key={label}>
          <span>{label}</span>
          <strong>{formatValue(value)}</strong>
        </div>
      ))}
      <div className="run-metadata">
        <span>Snapshot</span><code>{run.source_snapshot_id ?? "—"}</code>
        <span>Config hash</span><code>{run.config_hash ?? "—"}</code>
      </div>
    </div>
  );
}

function EmptyPanel({ title, copy }: { title: string; copy: string }) {
  return <div className="inspector-empty"><strong>{title}</strong><span>{copy}</span></div>;
}

export function Inspector({ run, sources, activeTab, onTabChange }: InspectorProps) {
  return (
    <aside className="inspector" aria-label="Run inspector">
      <div className="inspector-header">
        <div>
          <p className="eyebrow">Inspector</p>
          <h2>{run ? `Run ${run.run_id.slice(-6)}` : "No active run"}</h2>
        </div>
        <StatusBadge status={run?.status} />
      </div>
      <div className="inspector-tabs" role="tablist" aria-label="Run details">
        {tabs.map((tab) => (
          <button
            className={activeTab === tab.id ? "inspector-tab inspector-tab-active" : "inspector-tab"}
            type="button"
            role="tab"
            aria-selected={activeTab === tab.id}
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div className="inspector-content">
        {activeTab === "evidence" && <EvidencePanel run={run} />}
        {activeTab === "sources" && <SourcesPanel sources={sources} />}
        {activeTab === "metrics" && <MetricsPanel run={run} />}
      </div>
      {run && (
        <div className="inspector-footer">
          <span>{run.provider ?? "provider unknown"}</span>
          <span>{run.model ?? "model unknown"}</span>
        </div>
      )}
    </aside>
  );
}
