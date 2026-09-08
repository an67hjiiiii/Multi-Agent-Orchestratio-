import { useRef } from "react";
import type { SourceSummary } from "../types/api";
import type { SourceImportState } from "../app/useResearchApp";
import { KnowledgeSourceList } from "./KnowledgeSourceList";

interface KnowledgeWorkspaceProps {
  sources: SourceSummary[];
  sourceSnapshotId: string | null;
  sourceImport: SourceImportState;
  isImporting: boolean;
  onImport: (file: File) => Promise<void>;
  onInspectChunk: (chunkId: string) => void;
}

function snapshotLabel(snapshotId: string | null) {
  if (!snapshotId) return "Not recorded";
  if (snapshotId.length <= 18) return snapshotId;
  return `${snapshotId.slice(0, 8)}…${snapshotId.slice(-6)}`;
}

function SourceImportStatus({ state }: { state: SourceImportState }) {
  if (state.phase === "idle") return null;

  const isError = state.phase === "error";
  const isComplete = state.phase === "complete";
  const activeStep = state.phase === "indexing" || isComplete ? 1 : 0;
  const steps = ["Upload request", "Index chunks"];

  return (
    <div
      className={`knowledge-import-status knowledge-import-status-${state.phase}`}
      role={isError ? "alert" : "status"}
      aria-live="polite"
    >
      <div className="knowledge-import-heading">
        <div>
          <strong>{isError ? "Source import stopped" : isComplete ? "Source ready" : "Adding source"}</strong>
          <span>{state.fileName ?? "Selected file"}</span>
        </div>
        {state.result && <code>{state.result.total_chunks_for_source} chunks</code>}
      </div>
      <ol className="knowledge-import-steps" aria-label="Source import progress">
        {steps.map((step, index) => {
          const stepState = isError && index === activeStep
            ? "error"
            : isComplete || index < activeStep
              ? "complete"
              : index === activeStep
                ? "active"
                : "waiting";
          return (
            <li className={`knowledge-import-step knowledge-import-step-${stepState}`} key={step}>
              <span aria-hidden="true">{stepState === "complete" ? "✓" : stepState === "error" ? "!" : String(index + 1)}</span>
              {step}
            </li>
          );
        })}
      </ol>
      {state.message && <p>{state.message}</p>}
    </div>
  );
}

export function KnowledgeWorkspace({
  sources,
  sourceSnapshotId,
  sourceImport,
  isImporting,
  onImport,
  onInspectChunk,
}: KnowledgeWorkspaceProps) {
  const fileRef = useRef<HTMLInputElement>(null);
  const totalChunks = sources.reduce((total, source) => total + source.chunk_count, 0);

  return (
    <section className="knowledge-workspace" aria-labelledby="knowledge-workspace-title">
      <div className="knowledge-workspace-heading">
        <div>
          <span className="section-eyebrow">Local knowledge base</span>
          <h3 id="knowledge-workspace-title">Corpus workspace</h3>
          <p>Keep source availability, indexing, and readable chunk context in one place.</p>
        </div>
        <div className="knowledge-workspace-actions">
          <input
            ref={fileRef}
            className="visually-hidden"
            type="file"
            accept=".txt,.md,.markdown,.py,.js,.ts,.tsx,.json,.yaml,.yml,.csv"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) void onImport(file);
              event.target.value = "";
            }}
          />
          <button className="knowledge-add-button" type="button" onClick={() => fileRef.current?.click()} disabled={isImporting}>
            <span aria-hidden="true">＋</span>
            {isImporting ? "Adding source…" : "Add source"}
          </button>
        </div>
      </div>

      <div className="knowledge-summary" aria-label="Knowledge base summary">
        <div><span>Documents</span><strong>{sources.length}</strong></div>
        <div><span>Indexed chunks</span><strong>{totalChunks}</strong></div>
        <div><span>Corpus snapshot</span><code title={sourceSnapshotId ?? "Snapshot not recorded"}>{snapshotLabel(sourceSnapshotId)}</code></div>
      </div>

      <SourceImportStatus state={sourceImport} />
      <KnowledgeSourceList sources={sources} onInspectChunk={onInspectChunk} />
    </section>
  );
}
