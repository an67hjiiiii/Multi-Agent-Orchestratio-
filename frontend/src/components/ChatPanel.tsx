import type { RunMetrics, RunRecord, RunStatus } from "../types/api";
import { ChatComposer } from "./ChatComposer";
import { getStatusTone, normalizeStatus, StatusBadge } from "./StatusBadge";

interface ChatPanelProps {
  run: RunRecord | null;
  pendingQuestion?: string | null;
  condition?: string;
  provider?: string;
  isRunning: boolean;
  isImporting: boolean;
  sourceNotice: string | null;
  onSubmit: (message: string) => Promise<void>;
  onImport: (file: File) => Promise<void>;
}

const statusDescriptions: Record<string, string> = {
  READY: "Ready for a new question",
  RUNNING: "Retrieving evidence and generating an answer",
  COMPLETE: "Answer ready",
  PARTIAL: "Answer needs review",
  NO_EVIDENCE: "No validated evidence found",
  FAILED: "Run failed",
};

export function getChatStatus(run: RunRecord | null, isRunning: boolean): RunStatus {
  return isRunning ? "RUNNING" : run?.status ?? "READY";
}

export function formatMetricValue(
  value: number | string | null | undefined,
  suffix = "",
): string {
  if (value === null || value === undefined || value === "") return "—";
  const formatted = typeof value === "number" ? new Intl.NumberFormat().format(value) : value;
  return `${formatted}${suffix}`;
}

function unique(values: string[]): string[] {
  return Array.from(new Set(values.filter(Boolean)));
}

function statusDescription(status: RunStatus): string {
  return statusDescriptions[normalizeStatus(status)] ?? "Run status received";
}

function RunStatusCard({
  run,
  status,
  condition,
  provider,
}: {
  run: RunRecord | null;
  status: RunStatus;
  condition: string;
  provider: string;
}) {
  const normalizedStatus = normalizeStatus(status);
  const runId = run?.run_id;

  return (
    <section className={`run-status-card run-status-${getStatusTone(normalizedStatus)}`} aria-label="Current run status">
      <div className="run-status-summary">
        <span className="run-status-kicker">Run status</span>
        <div className="run-status-value">
          <StatusBadge status={normalizedStatus} />
          <span>{statusDescription(normalizedStatus)}</span>
        </div>
      </div>
      <dl className="run-status-meta">
        <div><dt>Condition</dt><dd>{run?.condition ?? condition}</dd></div>
        <div><dt>Profile</dt><dd>{run?.implementation_profile ?? "vanilla-rag"}</dd></div>
        <div><dt>Provider</dt><dd>{run?.provider ?? provider}</dd></div>
        <div><dt>Run</dt><dd title={runId}>{runId ? runId.slice(-8) : "pending"}</dd></div>
      </dl>
    </section>
  );
}

function RuntimeMetrics({ metrics }: { metrics?: RunMetrics }) {
  const totalTokens = metrics?.total_tokens ?? (
    typeof metrics?.input_tokens === "number" && typeof metrics.output_tokens === "number"
      ? metrics.input_tokens + metrics.output_tokens
      : undefined
  );
  const entries = [
    ["Latency", formatMetricValue(metrics?.latency_ms, " ms")],
    ["LLM calls", formatMetricValue(metrics?.llm_calls)],
    ["Tokens", formatMetricValue(totalTokens)],
    ["Selected chunks", formatMetricValue(metrics?.selected_chunks)],
    ["Valid citations", formatMetricValue(metrics?.citations_valid)],
  ] as const;
  const hasValues = entries.some(([, value]) => value !== "—");

  return (
    <section className="run-metrics" aria-label="Basic runtime metrics">
      <div className="run-metrics-heading"><span>Runtime metrics</span><span>Quality not evaluated</span></div>
      {hasValues ? (
        <div className="run-metrics-grid">
          {entries.map(([label, value]) => <div className="run-metric" key={label}><span>{label}</span><strong>{value}</strong></div>)}
        </div>
      ) : <p className="run-metrics-empty">This run did not return runtime measurements.</p>}
    </section>
  );
}

function AnswerBlock({ run, citations }: { run: RunRecord; citations: string[] }) {
  const missingInformation = unique((run.task_results ?? []).flatMap((result) => result.missing_information ?? []));
  const invalidCitations = unique((run.task_results ?? []).flatMap((result) => result.invalid_citations ?? []));
  const answer = run.answer?.trim();

  return (
    <section className={`answer-block answer-${getStatusTone(run.status)}`} aria-label="Research answer">
      <div className="answer-heading">
        <div className="answer-heading-identity">
          <span className="answer-avatar" aria-hidden="true">LR</span>
          <div><span className="message-label">Research answer</span><span className="answer-meta">Condition {run.condition ?? "A"} · source-grounded</span></div>
        </div>
        <StatusBadge status={run.status} />
      </div>
      {answer ? <p className="answer-copy">{answer}</p> : run.error ? <p className="answer-error" role="alert">{run.error}</p> : <p className="answer-copy answer-copy-muted">No answer was returned for this run.</p>}
      {missingInformation.length > 0 && <div className="answer-note"><strong>Missing information</strong><span>{missingInformation.join(" · ")}</span></div>}
      {citations.length > 0 && <div className="answer-citations"><span className="citation-label">Validated citations</span>{citations.map((citation) => <span className="citation-chip" key={citation}>{citation}</span>)}</div>}
      {invalidCitations.length > 0 && <p className="citation-warning">{invalidCitations.length} citation{invalidCitations.length === 1 ? "" : "s"} were excluded because their locators could not be validated.</p>}
      <RuntimeMetrics metrics={run.metrics} />
    </section>
  );
}

function PendingAnswer() {
  return (
    <section className="answer-block answer-pending" aria-label="Answer in progress">
      <div className="answer-heading">
        <div className="answer-heading-identity"><span className="answer-avatar" aria-hidden="true">LR</span><div><span className="message-label">Research answer</span><span className="answer-meta">Waiting for the bounded local run</span></div></div>
        <StatusBadge status="RUNNING" />
      </div>
      <p className="answer-copy answer-copy-muted">Retrieving local evidence and validating citations…</p>
    </section>
  );
}

export function ChatPanel({
  run,
  pendingQuestion = null,
  condition = "A",
  provider = "local",
  isRunning,
  isImporting,
  sourceNotice,
  onSubmit,
  onImport,
}: ChatPanelProps) {
  const status = getChatStatus(run, isRunning);
  const citations = unique((run?.task_results ?? []).flatMap((result) => result.citations ?? []));

  return (
    <main className="chat-panel">
      <div className="chat-header">
        <div>
          <p className="eyebrow">M0 research console</p>
          <h1>Explore your evidence</h1>
        </div>
        <div className="chat-header-note">
          <StatusBadge status={status} compact />
          <span>Runs stay on this machine</span>
        </div>
      </div>

      <div className="conversation" aria-live="polite" aria-busy={isRunning}>
        {!run && !pendingQuestion && !isRunning ? (
          <div className="welcome-state">
            <div className="welcome-kicker">LOCAL MULTI-AGENT RAG</div>
            <h2>Start with a focused research question.</h2>
            <p>
              Import a text source, then run a question to inspect the answer, evidence trace,
              and runtime metrics together.
            </p>
            <div className="welcome-prompts" aria-label="Example research questions">
              <span>“What risks are documented in this corpus?”</span>
              <span>“Summarize the API architecture evidence.”</span>
            </div>
          </div>
        ) : (
          <article className="conversation-thread">
            <div className="user-message">
              <div className="message-topline">
                <span className="message-label">You</span>
                {isRunning && <span className="message-state">New run in progress</span>}
              </div>
              <p>{pendingQuestion ?? run?.query ?? "Research question"}</p>
            </div>
            <RunStatusCard run={run} status={status} condition={condition} provider={provider} />
            {isRunning || !run ? <PendingAnswer /> : <AnswerBlock run={run} citations={citations} />}
          </article>
        )}

        {isRunning && (
          <div className="running-callout" role="status">
            <span className="loading-bar" aria-hidden="true" />
            <span>Running the local pipeline and assembling evidence…</span>
          </div>
        )}
      </div>

      <div className="composer-dock">
        {sourceNotice && <div className="source-notice" role="status">{sourceNotice}</div>}
        <ChatComposer isRunning={isRunning} isImporting={isImporting} onSubmit={onSubmit} onImport={onImport} />
      </div>
    </main>
  );
}
