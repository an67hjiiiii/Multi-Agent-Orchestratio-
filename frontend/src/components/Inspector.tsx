import { useState } from "react";
import type { InspectorTab } from "../app/useResearchApp";
import type { RunRecord, SourceChunk, SourceDetail, SourceSummary } from "../types/api";
import { ownerScopedRetrieval } from "../lib/api";
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

function unique(values: string[]) {
  return [...new Set(values.filter(Boolean))];
}

export function getEvidenceEvents(run: RunRecord | null) {
  return (run?.events ?? []).filter(
    (event) => Boolean(event.selected?.length || event.dropped?.length),
  );
}

export function getEvidenceIds(run: RunRecord | null) {
  return unique([
    ...(run?.events ?? []).flatMap((event) => event.selected ?? []),
    ...(run?.events ?? []).flatMap((event) => event.result?.evidence_ids ?? []),
    ...(run?.task_results ?? []).flatMap((result) => result.evidence_ids ?? []),
  ]);
}

export function getRunCitations(run: RunRecord | null) {
  return {
    valid: unique([
      ...(run?.events ?? []).flatMap((event) => event.result?.citations ?? []),
      ...(run?.task_results ?? []).flatMap((result) => result.citations ?? []),
    ]),
    invalid: unique([
      ...(run?.events ?? []).flatMap((event) => event.result?.invalid_citations ?? []),
      ...(run?.task_results ?? []).flatMap((result) => result.invalid_citations ?? []),
    ]),
  };
}

function ChunkPreview({ chunk, onClose }: { chunk: SourceChunk; onClose: () => void }) {
  const score = chunk.score === undefined ? "" : ` · score ${chunk.score.toFixed(3)}`;
  return (
    <div className="chunk-preview" aria-live="polite">
      <div className="chunk-preview-heading">
        <span title={chunk.chunk_id}>{chunk.chunk_id}</span>
        <button type="button" className="close-preview" aria-label="Close source preview" onClick={onClose}>×</button>
      </div>
      <div className="source-card-meta">{chunk.source_name} · chunk {chunk.index + 1}{score}</div>
      <pre aria-label={`Text from ${chunk.chunk_id}`}>{chunk.text}</pre>
    </div>
  );
}

function InspectableIds({
  ids,
  loadingId,
  onInspect,
  emptyLabel = "None recorded",
}: {
  ids: string[];
  loadingId: string | null;
  onInspect: (id: string) => void;
  emptyLabel?: string;
}) {
  if (ids.length === 0) return <span className="source-card-meta">{emptyLabel}</span>;
  return (
    <div>
      {ids.map((id) => (
        <button
          type="button"
          className="evidence-id text-button"
          key={id}
          disabled={loadingId !== null && loadingId !== id}
          aria-label={`Inspect evidence ${id}`}
          onClick={() => onInspect(id)}
        >
          {loadingId === id ? "Loading…" : id}
        </button>
      ))}
    </div>
  );
}

function EvidencePanel({ run }: { run: RunRecord | null }) {
  const [selectedChunk, setSelectedChunk] = useState<SourceChunk | null>(null);
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [chunkError, setChunkError] = useState<string | null>(null);
  const events = getEvidenceEvents(run);
  const results = run?.task_results ?? [];
  const citations = getRunCitations(run);

  async function inspectChunk(chunkId: string) {
    setLoadingId(chunkId);
    setChunkError(null);
    try {
      setSelectedChunk(await ownerScopedRetrieval.getChunk(chunkId));
    } catch (cause) {
      setSelectedChunk(null);
      setChunkError(cause instanceof Error ? cause.message : "Unable to load this evidence");
    } finally {
      setLoadingId(null);
    }
  }

  if (!run) return <EmptyPanel title="No run selected" copy="Evidence will appear after your first run." />;
  if (events.length === 0 && results.length === 0) return <EmptyPanel title="No evidence trace" copy="This run did not return retrieval events." />;

  return (
    <div className="inspector-list">
      {events.length === 0 ? (
        <EmptyPanel title="No retrieval trace" copy="This run returned task results without retrieval events." />
      ) : (
        events.map((event, index) => {
          const selected = unique(event.selected ?? []);
          const dropped = unique((event.dropped ?? []).map((item) => item.chunk_id ?? ""));
          return (
            <div className="evidence-card" key={`${event.stage}-${event.task_id ?? index}`}>
              <div className="evidence-card-heading">
                <span>{event.task_id ?? "Run retrieval"}</span>
                <span className="evidence-stage">{event.stage}</span>
              </div>
              <div className="evidence-row"><span>Selected evidence</span><strong>{selected.length}</strong></div>
              <InspectableIds ids={selected} loadingId={loadingId} onInspect={(id) => void inspectChunk(id)} />
              <div className="evidence-row evidence-row-muted"><span>Dropped evidence</span><strong>{event.dropped?.length ?? 0}</strong></div>
              {dropped.length > 0 && <InspectableIds ids={dropped} loadingId={loadingId} onInspect={(id) => void inspectChunk(id)} emptyLabel="No chunk locator" />}
              {event.dropped?.map((item, droppedIndex) => (
                <div className="source-card-meta" key={`${item.chunk_id ?? "dropped"}-${droppedIndex}`}>
                  {item.reason ?? "Dropped by context budget"}{item.estimated_tokens === undefined ? "" : ` · ${item.estimated_tokens} tokens`}
                </div>
              ))}
            </div>
          );
        })
      )}

      {results.length > 0 && (
        <div className="evidence-card">
          <div className="evidence-card-heading"><span>Citation audit</span><span className="evidence-stage">{citations.valid.length} valid · {citations.invalid.length} invalid</span></div>
          {results.map((result, index) => {
            const evidenceIds = unique(result.evidence_ids ?? []);
            const valid = unique(result.citations ?? []);
            const invalid = unique(result.invalid_citations ?? []);
            return (
              <div className="source-card" key={`${result.task_id}-${index}`}>
                <div className="source-card-heading"><span className="source-name">{result.task_id}{result.domain ? ` · ${result.domain}` : ""}</span><StatusBadge compact status={result.status} /></div>
                <div className="evidence-row"><span>Evidence IDs</span><strong>{evidenceIds.length}</strong></div>
                <InspectableIds ids={evidenceIds} loadingId={loadingId} onInspect={(id) => void inspectChunk(id)} />
                <div className="evidence-row"><span>Valid citations</span><strong>{valid.length}</strong></div>
                <InspectableIds ids={valid} loadingId={loadingId} onInspect={(id) => void inspectChunk(id)} />
                {invalid.length > 0 && <><div className="evidence-row evidence-row-muted"><span>Invalid citations</span><strong>{invalid.length}</strong></div><div>{invalid.map((id) => <code className="evidence-id" key={id}>{id}</code>)}</div></>}
                {(result.missing_information ?? []).length > 0 && <div className="source-card-meta">Missing: {result.missing_information?.join("; ")}</div>}
              </div>
            );
          })}
        </div>
      )}

      {chunkError && <div className="inspector-empty" role="alert"><strong>Unable to inspect evidence</strong><span>{chunkError}</span></div>}
      {selectedChunk && <ChunkPreview chunk={selectedChunk} onClose={() => setSelectedChunk(null)} />}
    </div>
  );
}

function sourceStatus(source: SourceSummary | SourceDetail): string {
  const explicit = "status" in source ? source.status : undefined;
  const indexed = "index_status" in source ? source.index_status : undefined;
  const reported = explicit ?? indexed;
  if (reported?.trim()) return reported;
  const chunkCount = "chunks" in source ? source.chunks.length : source.chunk_count;
  return chunkCount > 0 ? "READY" : "EMPTY";
}

function SourcesPanel({ sources }: { sources: SourceSummary[] }) {
  const [selectedSource, setSelectedSource] = useState<SourceDetail | null>(null);
  const [selectedChunk, setSelectedChunk] = useState<SourceChunk | null>(null);
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [sourceError, setSourceError] = useState<string | null>(null);

  async function inspectSource(source: SourceSummary) {
    setLoadingId(source.source_id);
    setSourceError(null);
    setSelectedChunk(null);
    try {
      setSelectedSource(await ownerScopedRetrieval.getSource(source.source_id));
    } catch (cause) {
      setSelectedSource(null);
      setSourceError(cause instanceof Error ? cause.message : "Unable to load this source");
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
            <StatusBadge compact status={sourceStatus(source)} />
          </div>
          <div className="source-card-meta">
            {source.chunk_count} {source.chunk_count === 1 ? "chunk" : "chunks"} · {source.source_id}
          </div>
          <button className="text-button" type="button" onClick={() => void inspectSource(source)} disabled={loadingId !== null}>
            {loadingId === source.source_id
              ? "Loading…"
              : selectedSource?.source_id === source.source_id
                ? "Refresh chunks"
                : "Inspect chunks"}
          </button>
        </div>
      ))}

      {sourceError && (
        <div className="inspector-empty" role="alert">
          <strong>Unable to load source</strong>
          <span>{sourceError}</span>
        </div>
      )}

      {selectedSource && (
        <div className="source-card">
          <div className="source-card-heading">
            <span className="source-name" title={selectedSource.source_name}>{selectedSource.source_name}</span>
            <StatusBadge compact status={sourceStatus(selectedSource)} />
            <button
              type="button"
              className="close-preview"
              aria-label="Close source details"
              onClick={() => {
                setSelectedSource(null);
                setSelectedChunk(null);
              }}
            >
              ×
            </button>
          </div>
          <div className="source-card-meta">
            {selectedSource.chunks.length} {selectedSource.chunks.length === 1 ? "chunk" : "chunks"} · {selectedSource.source_id}
          </div>
          {selectedSource.chunks.length === 0 ? (
            <span className="source-card-meta">This source has no stored chunks.</span>
          ) : (
            selectedSource.chunks.map((chunk) => (
              <div className="evidence-row" key={chunk.chunk_id}>
                <span>Chunk {chunk.index + 1}</span>
                <button
                  type="button"
                  className="text-button"
                  title={`Inspect ${chunk.chunk_id}`}
                  onClick={() => setSelectedChunk(chunk)}
                >
                  {chunk.chunk_id}
                </button>
              </div>
            ))
          )}
        </div>
      )}

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
