import { useMemo, useState } from "react";
import type { SourceChunk, SourceDetail, SourceSummary } from "../types/api";
import { api } from "../lib/api";

interface KnowledgeSourceListProps {
  sources: SourceSummary[];
  onInspectChunk: (chunkId: string) => void;
}

const sourceTypeByExtension: Record<string, string> = {
  csv: "CSV",
  js: "Code",
  json: "JSON",
  jsx: "Code",
  markdown: "Markdown",
  md: "Markdown",
  py: "Code",
  sh: "Code",
  sql: "Code",
  ts: "Code",
  tsx: "Code",
  txt: "Text",
  yaml: "YAML",
  yml: "YAML",
};

export function sourceType(sourceName: string) {
  const extension = sourceName.split(".").pop()?.toLowerCase() ?? "";
  return sourceTypeByExtension[extension] ?? "Text";
}

function sourceMark(sourceName: string) {
  const extension = sourceName.split(".").pop()?.toUpperCase() ?? "TXT";
  return extension === sourceName.toUpperCase() ? "TXT" : extension.slice(0, 4);
}

function SourceRow({
  source,
  selected,
  loading,
  busy,
  onInspect,
}: {
  source: SourceSummary;
  selected: boolean;
  loading: boolean;
  busy: boolean;
  onInspect: () => void;
}) {
  const indexed = source.chunk_count > 0;
  return (
    <article className={`knowledge-source-row${selected ? " knowledge-source-row-selected" : ""}`} role="listitem">
      <div className="knowledge-source-row-heading">
        <div className="knowledge-source-identity">
          <span className="knowledge-file-mark" aria-hidden="true">{sourceMark(source.source_name)}</span>
          <div>
            <h4 title={source.source_name}>{source.source_name}</h4>
            <p>{sourceType(source.source_name)} · {source.chunk_count} {source.chunk_count === 1 ? "chunk" : "chunks"}</p>
          </div>
        </div>
        <span className="knowledge-availability"><span aria-hidden="true" />Available locally</span>
      </div>
      <div className="knowledge-source-facts">
        <div><span>Type</span><strong>{sourceType(source.source_name)}</strong></div>
        <div><span>Chunks</span><strong>{source.chunk_count}</strong></div>
        <div><span>Status</span><strong>{indexed ? "Indexed" : "No chunks"}</strong></div>
      </div>
      <div className="knowledge-source-row-footer">
        <code title={source.source_id}>{source.source_id}</code>
        <button className="inline-action" type="button" onClick={onInspect} disabled={busy}>
          {loading ? "Loading source…" : selected ? "Source open" : "Inspect source"}
        </button>
      </div>
    </article>
  );
}

function ChunkExcerpt({ chunk, onInspect }: { chunk: SourceChunk; onInspect: () => void }) {
  return (
    <article className="knowledge-chunk-excerpt">
      <div className="knowledge-chunk-heading">
        <span>Chunk {String(chunk.index + 1).padStart(2, "0")}</span>
        <code title={chunk.chunk_id}>{chunk.chunk_id}</code>
      </div>
      <p>{chunk.text}</p>
      <button className="inline-action" type="button" onClick={onInspect}>
        Open in evidence <span aria-hidden="true">↗</span>
      </button>
    </article>
  );
}

export function KnowledgeSourceList({ sources, onInspectChunk }: KnowledgeSourceListProps) {
  const [search, setSearch] = useState("");
  const [selectedSource, setSelectedSource] = useState<SourceDetail | null>(null);
  const [loadingSourceId, setLoadingSourceId] = useState<string | null>(null);
  const [sourceError, setSourceError] = useState<string | null>(null);

  const filteredSources = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return sources;
    return sources.filter((source) =>
      [source.source_name, source.source_id, sourceType(source.source_name)]
        .some((value) => value.toLowerCase().includes(query)),
    );
  }, [search, sources]);

  async function inspectSource(sourceId: string) {
    setLoadingSourceId(sourceId);
    setSourceError(null);
    try {
      setSelectedSource(await api.getSource(sourceId));
    } catch (cause) {
      setSourceError(cause instanceof Error ? cause.message : "Unable to load source details");
    } finally {
      setLoadingSourceId(null);
    }
  }

  if (sources.length === 0) {
    return (
      <div className="knowledge-empty" role="status">
        <span className="knowledge-empty-mark" aria-hidden="true">⌁</span>
        <div>
          <strong>Your local corpus is empty</strong>
          <p>Add a UTF-8 text, markdown, or code file. The service will chunk it before it becomes available to retrieval.</p>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="knowledge-search">
        <label htmlFor="knowledge-search-input">Find a document</label>
        <div>
          <span aria-hidden="true">⌕</span>
          <input
            id="knowledge-search-input"
            type="search"
            value={search}
            placeholder="Search by name or type…"
            onChange={(event) => setSearch(event.target.value)}
          />
          {search && <button type="button" aria-label="Clear document search" onClick={() => setSearch("")}>×</button>}
        </div>
      </div>

      {sourceError && (
        <div className="knowledge-error" role="alert">
          <strong>Source details unavailable</strong>
          <span>{sourceError}</span>
        </div>
      )}

      {filteredSources.length === 0 ? (
        <div className="knowledge-empty knowledge-empty-compact" role="status">
          <strong>No documents match “{search}”</strong>
          <p>Try a different name, extension, or type.</p>
        </div>
      ) : (
        <div className="knowledge-source-list" role="list" aria-label="Loaded documents" aria-busy={loadingSourceId !== null}>
          {filteredSources.map((source) => (
            <SourceRow
              key={source.source_id}
              source={source}
              selected={selectedSource?.source_id === source.source_id}
              loading={loadingSourceId === source.source_id}
              busy={loadingSourceId !== null}
              onInspect={() => void inspectSource(source.source_id)}
            />
          ))}
        </div>
      )}

      {selectedSource && (
        <section className="knowledge-source-detail" aria-label={`Chunks in ${selectedSource.source_name}`}>
          <div className="knowledge-detail-heading">
            <div>
              <span className="section-eyebrow">Source inspection</span>
              <h4>{selectedSource.source_name}</h4>
              <p>{sourceType(selectedSource.source_name)} · {selectedSource.chunks.length} indexed {selectedSource.chunks.length === 1 ? "chunk" : "chunks"}</p>
            </div>
            <button className="icon-button" type="button" aria-label="Close source inspection" onClick={() => setSelectedSource(null)}>×</button>
          </div>
          <p className="knowledge-detail-copy">Read the stored excerpts here, then open a chunk in the evidence inspector to connect it to an answer citation.</p>
          {selectedSource.chunks.length === 0 ? (
            <div className="knowledge-empty knowledge-empty-compact" role="status"><strong>No indexed chunks returned</strong><p>This source is listed but has no readable context yet.</p></div>
          ) : (
            <div className="knowledge-chunk-list">
              {selectedSource.chunks.map((chunk) => <ChunkExcerpt key={chunk.chunk_id} chunk={chunk} onInspect={() => onInspectChunk(chunk.chunk_id)} />)}
            </div>
          )}
        </section>
      )}
    </>
  );
}
