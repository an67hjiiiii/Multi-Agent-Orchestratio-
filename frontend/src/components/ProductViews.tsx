import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import type {
  AdminStatusResponse,
  AdminUser,
  Conversation,
  HealthResponse,
  KnowledgeBaseStatus,
  RunListItem,
  SourceChunk,
  SourceDetail,
  SourceSummary,
} from "../types/api";
import type { SourceImportState } from "../app/useResearchApp";
import type { NormalizedUiRun } from "../lib/uiAdapter";
import { StatusBadge } from "./StatusBadge";

export function formatDate(value?: string) {
  if (!value) return "Date not recorded";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Date not recorded";
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "numeric" }).format(date);
}

function formatNumber(value: number | null | undefined) {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat().format(value);
}

function sourceChunks(sources: SourceSummary[]) {
  return sources.reduce((total, source) => total + (Number.isFinite(source.chunk_count) ? source.chunk_count : 0), 0);
}

export function HomeView({
  sources,
  history,
  health,
  onNewResearch,
  onKnowledge,
  onHistory,
  onSelectRun,
}: {
  sources: SourceSummary[];
  history: RunListItem[];
  health: HealthResponse | null;
  onNewResearch: () => void;
  onKnowledge: () => void;
  onHistory: () => void;
  onSelectRun: (runId: string) => void;
}) {
  const chunkCount = sourceChunks(sources);
  return (
    <div className="page-stack home-view">
      <section className="hero-block">
        <div>
          <p className="eyebrow">YOUR LOCAL RESEARCH DESK</p>
          <h1>Make the next question easier to trust.</h1>
          <p className="hero-copy">Ask a focused question, read the answer first, then follow the evidence back to the exact source chunk.</p>
        </div>
        <button className="button button-primary hero-action" type="button" onClick={onNewResearch}>Start new research <span aria-hidden="true">→</span></button>
      </section>

      <section className="home-metrics" aria-label="Workspace overview">
        <MetricCard label="Sources" value={formatNumber(sources.length)} detail={sources.length ? "Available locally" : "Add your first source"} tone="teal" onClick={onKnowledge} />
        <MetricCard label="Indexed chunks" value={formatNumber(chunkCount)} detail={health?.knowledge_base?.status === "READY" ? "Ready for retrieval" : "Waiting for a source"} tone="slate" onClick={onKnowledge} />
        <MetricCard label="Saved runs" value={formatNumber(history.length)} detail={history.length ? "Reopen any answer" : "Your runs appear here"} tone="amber" onClick={onHistory} />
      </section>

      <div className="home-columns">
        <section className="surface-card home-start-card" aria-labelledby="home-start-title">
          <div className="section-heading"><div><p className="eyebrow">A SMALL, TRACEABLE LOOP</p><h2 id="home-start-title">Question → answer → source</h2></div><span className="section-mark" aria-hidden="true">↗</span></div>
          <div className="evidence-loop" aria-label="Research flow">
            <div><span>01</span><strong>Ask</strong><small>Write what you need to understand.</small></div>
            <div><span>02</span><strong>Read</strong><small>See a bounded answer with its status.</small></div>
            <div><span>03</span><strong>Trace</strong><small>Open the exact supporting chunk.</small></div>
          </div>
          <button className="text-link" type="button" onClick={onNewResearch}>Open the research workspace <span aria-hidden="true">→</span></button>
        </section>

        <RecentRunsCard history={history} onSelectRun={onSelectRun} onViewAll={onHistory} />
      </div>
    </div>
  );
}

function MetricCard({ label, value, detail, tone, onClick }: { label: string; value: string; detail: string; tone: "teal" | "slate" | "amber"; onClick: () => void }) {
  return (
    <button className={`metric-card metric-card-${tone}`} type="button" onClick={onClick}>
      <span>{label}</span><strong>{value}</strong><small>{detail} <span aria-hidden="true">→</span></small>
    </button>
  );
}

function RecentRunsCard({ history, onSelectRun, onViewAll }: { history: RunListItem[]; onSelectRun: (runId: string) => void; onViewAll: () => void }) {
  return (
    <section className="surface-card recent-runs-card" aria-labelledby="recent-runs-title">
      <div className="section-heading"><div><p className="eyebrow">KEEP YOUR THREAD</p><h2 id="recent-runs-title">Recent research</h2></div><button className="text-link" type="button" onClick={onViewAll}>View all <span aria-hidden="true">→</span></button></div>
      {history.length === 0 ? <EmptyState title="No saved research yet" copy="Start with one focused question and your run will appear here." actionLabel="Start research" onAction={onViewAll} /> : (
        <div className="recent-run-list">
          {history.slice(0, 4).map((item) => (
            <button className="recent-run-item" type="button" key={item.run_id} onClick={() => onSelectRun(item.run_id)}>
              <span className="recent-run-icon" aria-hidden="true">⌁</span>
              <span className="recent-run-copy"><strong>{item.query || "Untitled research"}</strong><small>{formatDate(item.created_at)}</small></span>
              <StatusBadge status={item.status} compact />
              <span className="row-arrow" aria-hidden="true">→</span>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}

export function ResearchView({
  conversation,
  run,
  pendingQuestion,
  isRunning,
  isImporting,
  sourceNotice,
  provider,
  onProviderChange,
  onSubmit,
  onNewConversation,
  onImport,
  onOpenInspector,
  onOpenCitation,
}: {
  conversation: Conversation | null;
  run: NormalizedUiRun | null;
  pendingQuestion: string | null;
  isRunning: boolean;
  isImporting: boolean;
  sourceNotice: string | null;
  provider: string;
  onProviderChange: (provider: string) => void;
  onSubmit: (message: string) => Promise<void>;
  onNewConversation: () => void;
  onImport: (file: File) => Promise<void>;
  onOpenInspector: (tab?: "run" | "evidence" | "history") => void;
  onOpenCitation: (citation: string) => void;
}) {
  const question = pendingQuestion ?? run?.raw.query ?? null;
  return (
    <div className="page-stack research-view">
      <section className="page-title-row">
        <div><p className="eyebrow">RESEARCH WORKSPACE</p><h1>{run ? "Continue the evidence thread" : "What do you want to understand?"}</h1><p>{run ? "Your answer is paired with an immutable run. Review support without losing the question." : "Start with a focused question against the sources stored on this machine."}</p></div>
        <div className="page-title-actions"><button className="button button-secondary" type="button" onClick={onNewConversation}>New conversation <span aria-hidden="true">＋</span></button>{run && <button className="button button-secondary" type="button" onClick={() => onOpenInspector("run")}>Open run inspector <span aria-hidden="true">↗</span></button>}</div>
      </section>

      {conversation && <ConversationThread conversation={conversation} />}
      <ResearchComposer isRunning={isRunning} isImporting={isImporting} provider={provider} onProviderChange={onProviderChange} onSubmit={onSubmit} onImport={onImport} />
      {sourceNotice && <div className="notice notice-success" role="status"><span aria-hidden="true">✓</span>{sourceNotice}</div>}

      {!run && !isRunning && <section className="surface-card research-ready" aria-label="Ready to research"><span className="ready-orbit" aria-hidden="true">⌁</span><div><h2>Ready when you are.</h2><p>Import a source or ask a question. The answer will stay here, with source context one click away.</p></div></section>}
      {isRunning && <ResearchLoading question={question} />}
      {!isRunning && run && <RunResult run={run} onOpenInspector={onOpenInspector} onOpenCitation={onOpenCitation} />}
    </div>
  );
}

function ConversationThread({ conversation }: { conversation: Conversation }) {
  if (!conversation.messages.length) return <section className="surface-card conversation-thread" aria-label="New conversation"><div className="section-heading"><div><p className="eyebrow">NEW CONVERSATION</p><h2>{conversation.title}</h2></div></div><p className="conversation-empty">This thread is ready. Your first question will start a bounded, local context.</p></section>;
  return <section className="surface-card conversation-thread" aria-label="Conversation turns"><div className="section-heading"><div><p className="eyebrow">CONVERSATION</p><h2>{conversation.title}</h2></div><span className="section-count">{conversation.messages.length}</span></div><div className="conversation-turns">{conversation.messages.map((message) => <article className={`conversation-turn conversation-turn-${message.role.toLowerCase()}`} key={message.message_id}><div className="conversation-turn-label">{message.role === "USER" ? "You" : "Assistant"}<small>{formatDate(message.created_at)}</small></div><p>{message.content}</p>{message.run_id && <small className="conversation-run-link">Run {message.run_id}</small>}</article>)}</div></section>;
}

export function ResearchComposer({
  isRunning,
  isImporting,
  provider,
  onProviderChange,
  onSubmit,
  onImport,
}: {
  isRunning: boolean;
  isImporting: boolean;
  provider: string;
  onProviderChange: (provider: string) => void;
  onSubmit: (message: string) => Promise<void>;
  onImport: (file: File) => Promise<void>;
}) {
  const [message, setMessage] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  async function submit() {
    const trimmed = message.trim();
    if (!trimmed || isRunning) return;
    try {
      await onSubmit(trimmed);
      setMessage("");
    } catch {
      // The app-level error keeps the draft visible so the user can recover.
    }
  }

  return (
    <section className="composer-card" aria-labelledby="research-composer-title">
      <div className="composer-card-heading"><div><p className="eyebrow">ASK THE CORPUS</p><h2 id="research-composer-title">Write a question worth tracing</h2></div><span className="composer-private"><span aria-hidden="true">◉</span> Local only</span></div>
      <form className="research-form" aria-busy={isRunning} onSubmit={(event) => { event.preventDefault(); void submit(); }}>
        <label className="visually-hidden" htmlFor="research-question-v4">Research question</label>
        <textarea id="research-question-v4" rows={4} value={message} disabled={isRunning} placeholder="For example: What does the project say about its retrieval limits?" onChange={(event) => setMessage(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) { event.preventDefault(); void submit(); } }} />
        <div className="composer-footer"><div className="composer-tools"><input ref={fileRef} className="visually-hidden" id="research-source-v4" type="file" accept=".txt,.md,.markdown,.pdf,.py,.js,.ts,.tsx,.json,.yaml,.yml,.csv" onChange={(event) => { const file = event.target.files?.[0]; if (file) void onImport(file); event.target.value = ""; }} /><label className="button button-quiet" htmlFor="research-source-v4"><span aria-hidden="true">＋</span> Add source</label><details className="composer-settings"><summary>Run settings</summary><div className="composer-settings-panel"><span className="field-label">Provider</span><strong>{provider === "ollama" ? "Local Ollama" : "Runtime-selected local provider"}</strong><small>Provider identity is returned with each run. No credentials are stored here.</small></div></details></div><button className="button button-primary composer-submit" type="submit" disabled={isRunning || !message.trim()}>{isRunning ? "Running locally…" : "Run research"}<span aria-hidden="true">→</span></button></div>
      </form>
      <p className="composer-help">Press Ctrl/⌘ + Enter to run · UTF-8 text and code sources up to 2 MB</p>
      {isImporting && <div className="inline-loading" role="status"><span className="loading-dot" aria-hidden="true" /> Adding and indexing your source…</div>}
    </section>
  );
}

function ResearchLoading({ question }: { question: string | null }) {
  return (
    <section className="loading-card" role="status" aria-live="polite" aria-label="Research in progress">
      <div className="loading-spinner" aria-hidden="true" /><div><p className="eyebrow">RUNNING LOCALLY</p><h2>Following the evidence trail…</h2><p>{question || "Your question is being prepared."}</p><small>The final run status and citations will appear when the local service responds.</small></div>
    </section>
  );
}

export function RunResult({ run, onOpenInspector, onOpenCitation }: { run: NormalizedUiRun; onOpenInspector: (tab?: "run" | "evidence" | "history") => void; onOpenCitation: (citation: string) => void }) {
  const stateCopy: Record<string, { title: string; copy: string }> = {
    COMPLETE: { title: "Answer ready", copy: "The run returned an answer with validated source locators." },
    PARTIAL: { title: "Answer needs review", copy: "The run returned useful information, but some requested details remain open." },
    NO_EVIDENCE: { title: "No supporting evidence was found", copy: "The current corpus did not return a validated source for this question." },
    FAILED: { title: "The run could not be completed", copy: "The local service stopped before producing a validated answer." },
    UNKNOWN: { title: "Run status needs attention", copy: "The service returned a status this interface does not recognize yet." },
  };
  const copy = stateCopy[run.state.kind] ?? stateCopy.UNKNOWN;
  const hasAnswer = run.answer.trim().length > 0;
  const fallback = run.state.kind === "NO_EVIDENCE" ? "No validated answer-domain evidence was found for this question." : run.state.kind === "FAILED" ? "No validated answer was produced for this run." : "No answer text was returned for this run.";
  return (
    <div className="run-result-stack">
      <section className={`run-status-card run-status-${run.state.kind.toLowerCase()}`} role={run.state.isError ? "alert" : "status"}>
        <div className="run-status-symbol" aria-hidden="true">{run.state.kind === "COMPLETE" ? "✓" : run.state.kind === "FAILED" ? "!" : run.state.kind === "NO_EVIDENCE" ? "∅" : "~"}</div><div><div className="run-status-heading"><strong>{copy.title}</strong><StatusBadge status={run.status} compact /></div><p>{copy.copy}</p>{run.researchFlags.isWiringOnly && <small>Fake provider result · wiring/test only, not semantic or milestone evidence.</small>}</div>
      </section>
      <article className="surface-card answer-card" aria-labelledby="answer-title-v4">
        <div className="answer-card-heading"><div><p className="eyebrow">ANSWER FIRST</p><h2 id="answer-title-v4">{run.raw.query || "Your research answer"}</h2></div><button className="text-link" type="button" onClick={() => onOpenInspector("run")}>Run details <span aria-hidden="true">↗</span></button></div>
        <div className={`answer-text${hasAnswer ? "" : " answer-text-muted"}`}>{hasAnswer ? run.answer : fallback}</div>
        {run.missingInformation.length > 0 && <div className="missing-note" role="note"><strong>What remains open</strong><ul>{run.missingInformation.map((item) => <li key={item}>{item}</li>)}</ul></div>}
        <EvidenceReviewInline run={run} onOpenInspector={onOpenInspector} onOpenCitation={onOpenCitation} />
      </article>
      <RunSummary run={run} onOpenInspector={onOpenInspector} />
    </div>
  );
}

function EvidenceReviewInline({ run, onOpenInspector, onOpenCitation }: { run: NormalizedUiRun; onOpenInspector: (tab?: "run" | "evidence" | "history") => void; onOpenCitation: (citation: string) => void }) {
  return (
    <section className="evidence-review-inline" aria-labelledby="evidence-review-title-v4">
      <div className="evidence-heading"><div><p className="eyebrow">EVIDENCE REVIEW</p><h3 id="evidence-review-title-v4">Supporting source chunks</h3></div><span className="evidence-count">{run.citations.length} valid</span></div>
      {run.citations.length > 0 ? <div className="citation-list">{run.citations.map((citation, index) => <button className="citation-row" type="button" key={citation} onClick={() => onOpenCitation(citation)}><span className="citation-number">{String(index + 1).padStart(2, "0")}</span><span><strong>Open source context</strong><code>{citation}</code></span><span aria-hidden="true">→</span></button>)}</div> : <div className="no-evidence-note"><strong>No validated citations returned.</strong><span>This answer view does not invent source links.</span></div>}
      {run.invalidCitations.length > 0 && <div className="invalid-note"><strong>{run.invalidCitations.length} locator{run.invalidCitations.length === 1 ? "" : "s"} needs review</strong><span>{run.invalidCitations.join(" · ")}</span></div>}
      <button className="button button-secondary evidence-open-button" type="button" onClick={() => onOpenInspector("evidence")}>Open evidence review <span aria-hidden="true">↗</span></button>
    </section>
  );
}

function RunSummary({ run, onOpenInspector }: { run: NormalizedUiRun; onOpenInspector: (tab?: "run" | "evidence" | "history") => void }) {
  const metrics = run.metrics;
  return <section className="run-summary"><div><p className="eyebrow">RUNTIME SNAPSHOT</p><h3>Measured run details</h3></div><div className="summary-grid"><div><span>Latency</span><strong>{metrics?.latency_ms === undefined ? "—" : `${formatNumber(metrics.latency_ms)} ms`}</strong></div><div><span>Selected chunks</span><strong>{formatNumber(metrics?.selected_chunks)}</strong></div><div><span>Valid citations</span><strong>{formatNumber(metrics?.citations_valid)}</strong></div></div><button className="text-link" type="button" onClick={() => onOpenInspector("run")}>View technical details <span aria-hidden="true">→</span></button></section>;
}

export function KnowledgeView({
  sources,
  sourceSnapshotId,
  knowledgeStatus,
  importState,
  isImporting,
  selectedSource,
  sourceLoadingId,
  sourceError,
  onImport,
  onInspectSource,
  onCloseSource,
  onInspectChunk,
}: {
  sources: SourceSummary[];
  sourceSnapshotId: string | null;
  knowledgeStatus?: KnowledgeBaseStatus;
  importState: SourceImportState;
  isImporting: boolean;
  selectedSource: SourceDetail | null;
  sourceLoadingId: string | null;
  sourceError: string | null;
  onImport: (file: File) => Promise<void>;
  onInspectSource: (source: SourceSummary) => void;
  onCloseSource: () => void;
  onInspectChunk: (chunk: SourceChunk) => void;
}) {
  const fileRef = useRef<HTMLInputElement>(null);
  const chunks = sourceChunks(sources);
  return (
    <div className="page-stack knowledge-view">
      <section className="page-title-row"><div><p className="eyebrow">KNOWLEDGE BASE</p><h1>Sources you can trace.</h1><p>Browse the local corpus, inspect chunks, and add a source when the answer needs more context.</p></div><div><input ref={fileRef} className="visually-hidden" id="knowledge-source-v4" type="file" accept=".txt,.md,.markdown,.pdf,.py,.js,.ts,.tsx,.json,.yaml,.yml,.csv" onChange={(event) => { const file = event.target.files?.[0]; if (file) void onImport(file); event.target.value = ""; }} /><label className="button button-primary" htmlFor="knowledge-source-v4" aria-disabled={isImporting}><span aria-hidden="true">＋</span> Add source</label></div></section>
      <section className="knowledge-summary-row" aria-label="Knowledge base summary"><div><span>Sources</span><strong>{formatNumber(sources.length)}</strong></div><div><span>Indexed chunks</span><strong>{formatNumber(chunks)}</strong></div><div><span>Status</span><strong>{knowledgeStatus?.status === "READY" ? "Ready" : knowledgeStatus?.status ?? "Not available"}</strong></div><div><span>Snapshot</span><code>{sourceSnapshotId || "Not recorded"}</code></div></section>
      {importState.phase !== "idle" && <ImportStatus state={importState} />}
      {sourceError && <div className="notice notice-error" role="alert"><strong>Source inspection unavailable</strong><span>{sourceError}</span></div>}
      {sources.length === 0 ? <section className="surface-card empty-panel"><span className="empty-mark" aria-hidden="true">▦</span><div><h2>Your corpus is empty.</h2><p>Add a UTF-8 text or code file to make the first source available for retrieval.</p></div><label className="button button-secondary" htmlFor="knowledge-source-v4">Add your first source</label></section> : <div className="knowledge-layout"><section className="source-list" aria-labelledby="source-list-title"><div className="section-heading"><div><p className="eyebrow">SOURCE LIBRARY</p><h2 id="source-list-title">Available sources</h2></div><span className="section-count">{sources.length}</span></div>{sources.map((source) => <SourceRow key={source.source_id} source={source} selected={selectedSource?.source_id === source.source_id} loading={sourceLoadingId === source.source_id} onInspect={() => onInspectSource(source)} />)}</section>{selectedSource ? <SourceDetailPanel source={selectedSource} onClose={onCloseSource} onInspectChunk={onInspectChunk} /> : <section className="surface-card source-placeholder"><span aria-hidden="true">⌁</span><h2>Select a source</h2><p>Open a source to see its chunks and read the provenance attached to each excerpt.</p></section>}</div>}
    </div>
  );
}

function SourceRow({ source, selected, loading, onInspect }: { source: SourceSummary; selected: boolean; loading: boolean; onInspect: () => void }) {
  const extension = source.source_name.split(".").pop()?.toUpperCase() || "TXT";
  return <button className={`source-row${selected ? " source-row-selected" : ""}`} type="button" onClick={onInspect}><span className="file-mark" aria-hidden="true">{extension.slice(0, 4)}</span><span className="source-row-copy"><strong title={source.source_name}>{source.source_name}</strong><small>{source.chunk_count} {source.chunk_count === 1 ? "chunk" : "chunks"} · {source.index_status || "Indexed locally"}</small></span><span className="source-row-action">{loading ? "Loading…" : selected ? "Open" : "Inspect"} <span aria-hidden="true">→</span></span></button>;
}

function SourceDetailPanel({ source, onClose, onInspectChunk }: { source: SourceDetail; onClose: () => void; onInspectChunk: (chunk: SourceChunk) => void }) {
  return <section className="surface-card source-detail-panel" aria-labelledby="source-detail-title"><div className="section-heading"><div><p className="eyebrow">SOURCE DETAIL</p><h2 id="source-detail-title">{source.source_name}</h2><p>{source.chunks.length} {source.chunks.length === 1 ? "chunk" : "chunks"} · {source.source_id}</p></div><button className="icon-button" type="button" aria-label="Close source detail" onClick={onClose}>×</button></div>{source.chunks.length === 0 ? <div className="empty-inline"><strong>No chunks stored.</strong><span>This source is present but does not expose readable chunks.</span></div> : <div className="chunk-list">{source.chunks.map((chunk) => <button className="chunk-row" type="button" key={chunk.chunk_id} onClick={() => onInspectChunk(chunk)}><span className="chunk-index">{String(chunk.index + 1).padStart(2, "0")}</span><span><strong>{chunk.chunk_id}</strong><small>{chunk.text.slice(0, 150)}{chunk.text.length > 150 ? "…" : ""}</small></span><span aria-hidden="true">↗</span></button>)}</div>}</section>;
}

function ImportStatus({ state }: { state: SourceImportState }) {
  const labels: Record<SourceImportState["phase"], string> = { idle: "", uploading: "Uploading source…", indexing: "Indexing chunks…", complete: "Source ready", error: "Source could not be added" };
  return <div className={`import-status import-status-${state.phase}`} role={state.phase === "error" ? "alert" : "status"}><span className="import-status-dot" aria-hidden="true" /> <strong>{labels[state.phase]}</strong>{state.fileName && <span>{state.fileName}</span>}{state.message && <small>{state.message}</small>}</div>;
}

export function HistoryView({ conversations, activeConversationId, onNewConversation, onSelectConversation, history, activeRunId, onSelectRun }: { conversations: Conversation[]; activeConversationId?: string; onNewConversation: () => void; onSelectConversation: (conversationId: string) => void; history: RunListItem[]; activeRunId?: string; onSelectRun: (runId: string) => void }) {
  return <div className="page-stack history-view"><section className="page-title-row"><div><p className="eyebrow">HISTORY</p><h1>Return to a conversation without losing its trail.</h1><p>Threads group bounded turns; each answer still opens its immutable run and source evidence.</p></div><button className="button button-primary" type="button" onClick={onNewConversation}>New conversation <span aria-hidden="true">＋</span></button></section><section className="surface-card history-table" aria-labelledby="conversation-list-title"><div className="section-heading"><div><p className="eyebrow">CONVERSATIONS</p><h2 id="conversation-list-title">Your threads</h2></div><span className="section-count">{conversations.length}</span></div>{conversations.length === 0 ? <div className="empty-inline"><strong>No conversations yet.</strong><span>Start a new local thread from the research workspace.</span></div> : <div className="history-list">{conversations.map((conversation) => <button className={`history-row${conversation.conversation_id === activeConversationId ? " history-row-active" : ""}`} type="button" key={conversation.conversation_id} onClick={() => onSelectConversation(conversation.conversation_id)}><span className="history-row-marker" aria-hidden="true">↺</span><span className="history-row-copy"><strong>{conversation.title}</strong><small>{conversation.messages.length} turn{conversation.messages.length === 1 ? "" : "s"} · {formatDate(conversation.updated_at)}</small></span><span className="row-arrow" aria-hidden="true">→</span></button>)}</div>}</section><section className="surface-card history-table" aria-labelledby="history-list-title"><div className="section-heading"><div><p className="eyebrow">SAVED RUNS</p><h2 id="history-list-title">Run records</h2></div><span className="section-count">{history.length}</span></div>{history.length === 0 ? <div className="empty-inline"><strong>No saved runs yet.</strong><span>Runs will remain available as read-only research records.</span></div> : <div className="history-list">{history.map((item) => <button className={`history-row${item.run_id === activeRunId ? " history-row-active" : ""}`} type="button" key={item.run_id} onClick={() => onSelectRun(item.run_id)}><span className="history-row-marker" aria-hidden="true">⌁</span><span className="history-row-copy"><strong>{item.query || "Untitled research"}</strong><small>{formatDate(item.created_at)} · {item.run_id}</small></span><StatusBadge status={item.status} compact /><span className="row-arrow" aria-hidden="true">→</span></button>)}</div>}</section></div>;
}

export function SettingsView({ session, provider, onSignOut }: { session: { name: string; email: string; role: "researcher" | "admin"; demo: boolean }; provider: string; onSignOut: () => void }) {
  return <div className="page-stack settings-view"><section className="page-title-row"><div><p className="eyebrow">SETTINGS</p><h1>Keep the desk useful and understandable.</h1><p>These preferences belong to this local workspace. Runtime and research identity still come from the API.</p></div></section><section className="settings-grid"><div className="surface-card settings-card"><div className="settings-card-heading"><span className="settings-icon" aria-hidden="true">◉</span><div><p className="eyebrow">ACCOUNT</p><h2>{session.name}</h2><p>{session.email}</p></div></div><div className="settings-row"><span>Session</span><strong>Local account</strong></div><div className="settings-row"><span>Access level</span><strong>{session.role === "admin" ? "Administrator" : "Researcher"}</strong></div><button className="button button-secondary" type="button" onClick={onSignOut}>Sign out</button></div><div className="surface-card settings-card"><div><p className="eyebrow">RUN DEFAULTS</p><h2>Local provider</h2><p className="settings-copy">The runtime chooses the local provider. The selected identity is retained in the returned run when available.</p></div><div className="settings-row"><span>Provider</span><strong>{provider === "ollama" ? "Local Ollama" : "Runtime-selected local provider"}</strong></div><div className="settings-callout"><span aria-hidden="true">◉</span><span>Questions and sources stay on this machine. No hosted provider connection is configured here.</span></div></div><div className="surface-card settings-card settings-admin-card"><div><p className="eyebrow">ACCESS CONTROL</p><h2>Admin tools</h2><p className="settings-copy">Admin navigation is available only to local administrator accounts. Researcher accounts cannot elevate themselves.</p></div>{session.role === "admin" ? <div className="admin-access-granted" role="status"><span aria-hidden="true">✓</span> Administrator access is active for this local account.</div> : <div className="settings-callout"><span aria-hidden="true">◉</span><span>Ask a local administrator to grant access if needed.</span></div>}</div></section></div>;
}

export function AdminView({ sources, history, health }: { sources: SourceSummary[]; history: RunListItem[]; health: HealthResponse | null }) {
  const status = health?.knowledge_base?.status ?? "UNKNOWN";
  const [adminStatus, setAdminStatus] = useState<AdminStatusResponse | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [adminError, setAdminError] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    void Promise.all([api.adminStatus(), api.adminUsers()])
      .then(([runtime, userList]) => {
        if (!active) return;
        setAdminStatus(runtime);
        setUsers(userList.users);
      })
      .catch((cause) => {
        if (active) setAdminError(cause instanceof Error ? cause.message : "Admin data is unavailable");
      });
    return () => { active = false; };
  }, []);
  return <div className="page-stack admin-view"><section className="page-title-row"><div><p className="eyebrow">ADMIN · LOCAL ACCESS</p><h1>Workspace health at a glance.</h1><p>This read-only surface exposes available runtime facts without adding new backend authority.</p></div><span className="admin-badge">Administrator</span></section><section className="admin-grid"><div className="surface-card admin-status-card"><span className="admin-card-label">Runtime</span><strong>{health?.ok ? "Available" : "Unavailable"}</strong><small>{health?.version || "Version not returned"}</small></div><div className="surface-card admin-status-card"><span className="admin-card-label">Corpus</span><strong>{status === "READY" ? "Ready" : status}</strong><small>{sources.length} sources · {sourceChunks(sources)} chunks</small></div><div className="surface-card admin-status-card"><span className="admin-card-label">Saved runs</span><strong>{history.length}</strong><small>Read-only records available</small></div></section>{adminError && <div className="notice notice-error" role="alert"><strong>Admin data unavailable.</strong><span>{adminError}</span></div>}<section className="surface-card admin-note"><span className="settings-icon" aria-hidden="true">◆</span><div><h2>Guardrails stay visible.</h2><p>Administrator access does not expose credentials, change research configuration, delete sources, or promote a run to a quality or milestone decision.</p><small>{adminStatus?.auth?.user_count === undefined ? "Account count not available." : `${adminStatus.auth.user_count} local account${adminStatus.auth.user_count === 1 ? "" : "s"} · ${adminStatus.auth.active_session_count ?? 0} active session${adminStatus.auth.active_session_count === 1 ? "" : "s"}`}</small></div></section><section className="surface-card admin-user-card" aria-labelledby="admin-users-title"><div className="section-heading"><div><p className="eyebrow">LOCAL USERS</p><h2 id="admin-users-title">Accounts</h2></div><span className="section-count">{users.length}</span></div>{users.length === 0 ? <div className="empty-inline"><strong>No user records returned.</strong><span>Admin user management remains read-only in P0.</span></div> : <div className="admin-user-list">{users.map((user) => <div className="admin-user-row" key={user.user_id || user.id}><span className="account-avatar" aria-hidden="true">{(user.display_name || user.name || user.email || "?").slice(0, 1).toUpperCase()}</span><span><strong>{user.display_name || user.name || user.email || user.username || "Unnamed user"}</strong><small>{user.email || user.username || "No identifier"}</small></span><span className="admin-user-role">{user.role}</span><span className="admin-user-status">{user.status || "ACTIVE"}</span></div>)}</div>}</section></div>;
}

export function RunInspector({ run, history, activeTab, onTabChange, onClose, onSelectRun, onOpenCitation }: { run: NormalizedUiRun | null; history: RunListItem[]; activeTab: "run" | "evidence" | "history"; onTabChange: (tab: "run" | "evidence" | "history") => void; onClose: () => void; onSelectRun: (runId: string) => void; onOpenCitation: (citation: string) => void }) {
  return <aside className="inspector-drawer" aria-label="Run inspector"><div className="inspector-drawer-header"><div><p className="eyebrow">PROGRESSIVE DETAIL</p><h2>{activeTab === "run" ? "Run inspector" : activeTab === "evidence" ? "Evidence review" : "Research history"}</h2></div><button className="icon-button" type="button" aria-label="Close inspector" onClick={onClose}>×</button></div><div className="inspector-tabs" role="tablist" aria-label="Run details"><InspectorTab active={activeTab === "run"} label="Run" onClick={() => onTabChange("run")} /><InspectorTab active={activeTab === "evidence"} label="Evidence" onClick={() => onTabChange("evidence")} /><InspectorTab active={activeTab === "history"} label="History" onClick={() => onTabChange("history")} /></div><div className="inspector-body">{activeTab === "run" && <InspectorRun run={run} />}{activeTab === "evidence" && <InspectorEvidence run={run} onOpenCitation={onOpenCitation} />}{activeTab === "history" && <InspectorHistory history={history} activeRunId={run?.runId} onSelectRun={onSelectRun} />}</div></aside>;
}

function InspectorTab({ active, label, onClick }: { active: boolean; label: string; onClick: () => void }) { return <button className={`inspector-tab${active ? " inspector-tab-active" : ""}`} type="button" role="tab" aria-selected={active} onClick={onClick}>{label}</button>; }

function InspectorRun({ run }: { run: NormalizedUiRun | null }) {
  if (!run) return <EmptyState title="No active run" copy="Run details will appear after a question is submitted." />;
  const metrics = run.metrics;
  return <div className="inspector-stack"><div className="inspector-run-title"><span className="inspector-run-mark" aria-hidden="true">⌁</span><div><strong>{run.raw.query || "Untitled research"}</strong><small>{run.raw.created_at ? formatDate(run.raw.created_at) : "Date not recorded"}</small></div><StatusBadge status={run.status} compact /></div><div className="inspector-detail-list"><div><span>Provider</span><strong>{run.raw.provider || "Not recorded"}</strong></div><div><span>Model</span><strong>{run.raw.model || "Not recorded"}</strong></div><div><span>Source snapshot</span><code>{run.raw.source_snapshot_id || "Not recorded"}</code></div><div><span>Config identity</span><code>{run.raw.config_hash || "Not recorded"}</code></div><div><span>Trace events</span><strong>{run.traceSummary.eventCount}</strong></div></div>{run.researchFlags.isWiringOnly && <div className="inspector-boundary" role="note"><strong>Wiring/test only</strong><span>This provider result is not semantic or milestone evidence.</span></div>}{run.tasks.length > 0 && <section className="inspector-task-section" aria-labelledby="inspector-task-title"><div className="inspector-section-heading"><span id="inspector-task-title">Tasks and workers</span><strong>{run.tasks.length}</strong></div><div className="inspector-task-list">{run.tasks.map((task) => <article className="inspector-task-card" key={task.taskId}><div className="inspector-task-heading"><code>{task.taskId}</code><StatusBadge status={task.status ?? undefined} compact /></div><strong>{task.goal || "Task objective not returned"}</strong><small>{task.roleProfile || "Worker role not returned"}{task.domain ? ` · ${task.domain}` : ""}</small>{task.dependsOn.length > 0 && <small>Depends on: {task.dependsOn.join(", ")}</small>}{task.evidenceIds.length > 0 && <small>Evidence: {task.evidenceIds.join(", ")}</small>}</article>)}</div></section>}<details className="technical-disclosure"><summary>Show returned technical stages</summary><div className="technical-stage-list">{run.traceSummary.stages.length ? run.traceSummary.stages.map((stage) => <span key={stage}>{stage}</span>) : <small>No trace stages were returned.</small>}</div></details><details className="technical-disclosure"><summary>Show evidence allocation trace</summary><div className="technical-stage-list"><span>Selected evidence: {run.traceSummary.selectedCount}</span><span>Dropped evidence: {run.traceSummary.droppedCount}</span>{run.traceSummary.selectedEvidenceIds.length > 0 && <span>Selected IDs: {run.traceSummary.selectedEvidenceIds.join(", ")}</span>}{run.traceSummary.droppedEvidenceIds.length > 0 && <span>Dropped IDs: {run.traceSummary.droppedEvidenceIds.join(", ")}</span>}</div></details>{metrics && <div className="inspector-metrics"><span>Measured values</span><div><strong>{metrics.latency_ms === undefined ? "—" : `${formatNumber(metrics.latency_ms)} ms`}</strong><small>latency</small></div><div><strong>{formatNumber(metrics.total_tokens)}</strong><small>tokens</small></div></div>}</div>;
}

function InspectorEvidence({ run, onOpenCitation }: { run: NormalizedUiRun | null; onOpenCitation: (citation: string) => void }) {
  if (!run) return <EmptyState title="No evidence to review" copy="Submit a question to see returned citations." />;
  return <div className="inspector-stack"><div className="inspector-intro"><p>Open a valid locator to inspect the source chunk. Invalid locators remain visible but are not linked.</p></div>{run.citations.length ? <div className="inspector-citation-list">{run.citations.map((citation) => <button className="inspector-citation" type="button" key={citation} onClick={() => onOpenCitation(citation)}><span className="citation-valid" aria-hidden="true">✓</span><span><strong>Validated source chunk</strong><code>{citation}</code></span><span aria-hidden="true">↗</span></button>)}</div> : <div className="no-evidence-note"><strong>No validated citations returned.</strong><span>The run did not provide a source locator to open.</span></div>}{run.invalidCitations.length > 0 && <div className="invalid-note"><strong>Unresolved locators</strong><span>{run.invalidCitations.join(" · ")}</span></div>}{run.missingInformation.length > 0 && <div className="missing-note"><strong>Missing information</strong><ul>{run.missingInformation.map((item) => <li key={item}>{item}</li>)}</ul></div>}</div>;
}

function InspectorHistory({ history, activeRunId, onSelectRun }: { history: RunListItem[]; activeRunId?: string; onSelectRun: (runId: string) => void }) {
  if (!history.length) return <EmptyState title="No saved runs" copy="Completed questions will be available here." />;
  return <div className="inspector-history-list">{history.map((item) => <button className={`inspector-history-item${item.run_id === activeRunId ? " inspector-history-item-active" : ""}`} type="button" key={item.run_id} onClick={() => onSelectRun(item.run_id)}><span><strong>{item.query || "Untitled research"}</strong><small>{formatDate(item.created_at)}</small></span><StatusBadge status={item.status} compact /><span aria-hidden="true">→</span></button>)}</div>;
}

export function ChunkDialog({ chunk, onClose }: { chunk: SourceChunk; onClose: () => void }) {
  return <div className="dialog-backdrop" role="presentation"><section className="chunk-dialog" role="dialog" aria-modal="true" aria-labelledby="chunk-dialog-title"><div className="dialog-header"><div><p className="eyebrow">SOURCE CONTEXT</p><h2 id="chunk-dialog-title">{chunk.source_name}</h2></div><button className="icon-button" type="button" aria-label="Close source context" onClick={onClose}>×</button></div><div className="chunk-dialog-meta"><span>Chunk {chunk.index + 1}</span><code>{chunk.chunk_id}</code></div><p className="chunk-dialog-text">{chunk.text}</p><details className="technical-disclosure"><summary>Show provenance</summary><pre>{JSON.stringify(chunk.provenance || {}, null, 2)}</pre></details><div className="dialog-footer"><button className="button button-primary" type="button" onClick={onClose}>Return to research</button></div></section></div>;
}

export function EmptyState({ title, copy, actionLabel, onAction }: { title: string; copy: string; actionLabel?: string; onAction?: () => void }) {
  return <div className="empty-state" role="status"><span className="empty-mark" aria-hidden="true">⌁</span><div><strong>{title}</strong><p>{copy}</p>{actionLabel && onAction && <button className="button button-secondary" type="button" onClick={onAction}>{actionLabel} <span aria-hidden="true">→</span></button>}</div></div>;
}
