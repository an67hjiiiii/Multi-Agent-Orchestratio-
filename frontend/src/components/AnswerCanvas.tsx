import type { RunStatus, SourceSummary } from "../types/api";
import type { NormalizedUiRun } from "../lib/uiAdapter";
import { QuestionComposer } from "./QuestionComposer";
import { StatusBadge, getStatusLabel } from "./StatusBadge";
import type { ViewMode } from "./WorkspaceHeader";

interface AnswerCanvasProps {
  run: NormalizedUiRun | null;
  pendingQuestion: string | null;
  isRunning: boolean;
  isImporting: boolean;
  sourceNotice: string | null;
  provider: string;
  mode: ViewMode;
  sources: SourceSummary[];
  onProviderChange: (provider: string) => void;
  onSubmit: (message: string) => Promise<void>;
  onImport: (file: File) => Promise<void>;
  onOpenEvidence: (citation: string, trigger: HTMLButtonElement) => void;
  onOpenResearch: () => void;
  onOpenSources: () => void;
}

const statusCopy: Record<string, { title: string; body: string }> = {
  COMPLETE: {
    title: "Answer ready",
    body: "The run returned an answer and the evidence links below were validated by the application.",
  },
  PARTIAL: {
    title: "Answer needs review",
    body: "Some requested information or locators were not available in this run.",
  },
  NO_EVIDENCE: {
    title: "No validated evidence found",
    body: "The corpus did not return support for this question. Refine the question or add a source.",
  },
  FAILED: {
    title: "Run failed",
    body: "The local pipeline stopped before it produced a validated answer. Technical details remain available in Research / Demo mode.",
  },
  UNKNOWN: {
    title: "Run status received",
    body: "The service returned a status this interface does not recognize yet.",
  },
};

function metricValue(value: number | string | null | undefined, suffix = "") {
  if (value === null || value === undefined || value === "") return "—";
  const display = typeof value === "number" ? new Intl.NumberFormat().format(value) : value;
  return `${display}${suffix}`;
}

function RunStateBanner({ run }: { run: NormalizedUiRun }) {
  const copy = statusCopy[run.state.kind] ?? statusCopy.UNKNOWN;
  const role = run.state.isError ? "alert" : "status";
  const missingCount = run.missingInformation.length;

  return (
    <section className={`answer-state answer-state-${run.state.kind.toLowerCase()}`} role={role} aria-label="Run status">
      <div className="answer-state-mark" aria-hidden="true">
        {run.state.kind === "COMPLETE" ? "✓" : run.state.kind === "FAILED" ? "!" : run.state.kind === "NO_EVIDENCE" ? "∅" : "~"}
      </div>
      <div className="answer-state-copy">
        <div className="answer-state-heading">
          <strong>{copy.title}</strong>
          <StatusBadge status={run.state.kind as RunStatus} compact />
        </div>
        <p>{copy.body}</p>
        {missingCount > 0 && <small>{missingCount} missing-information note{missingCount === 1 ? "" : "s"} recorded.</small>}
        {run.researchFlags.isWiringOnly && <small>Fake provider result · wiring/test only, not semantic or milestone evidence.</small>}
      </div>
    </section>
  );
}

function LoadingProgress() {
  const steps = [
    { label: "Question received", state: "complete" },
    { label: "Retrieving local evidence", state: "active" },
    { label: "Validating citations", state: "waiting" },
    { label: "Preparing the answer", state: "waiting" },
  ];

  return (
    <section className="loading-progress" role="status" aria-label="Local run progress" aria-live="polite">
      <div className="loading-progress-heading">
        <div>
          <span className="section-eyebrow">Current run</span>
          <strong>Working locally</strong>
        </div>
        <span className="loading-stage-label">No cancellation available</span>
      </div>
      <ol className="loading-steps">
        {steps.map((step) => (
          <li className={`loading-step loading-step-${step.state}`} key={step.label}>
            <span className="loading-step-marker" aria-hidden="true">{step.state === "complete" ? "✓" : step.state === "active" ? "•" : ""}</span>
            <span>{step.label}</span>
          </li>
        ))}
      </ol>
      <p>Retrieving evidence and keeping your question visible while the bounded local run resolves.</p>
    </section>
  );
}

function EvidenceStrip({
  run,
  onOpenEvidence,
}: {
  run: NormalizedUiRun;
  onOpenEvidence: (citation: string, trigger: HTMLButtonElement) => void;
}) {
  return (
    <section className="validated-evidence" aria-labelledby="validated-evidence-title">
      <div className="validated-evidence-heading">
        <div>
          <span className="section-eyebrow">Evidence thread</span>
          <h3 id="validated-evidence-title">Validated evidence</h3>
        </div>
        <span className="validated-evidence-count">{run.citations.length} {run.citations.length === 1 ? "chunk" : "chunks"}</span>
      </div>
      <p>These chunks were returned as support for this task. Open one to read its source context.</p>
      <div className="citation-links">
        {run.citations.map((citation, index) => (
          <button
            className="citation-link"
            type="button"
            key={citation}
            title={`View evidence for ${citation}`}
            onClick={(event) => onOpenEvidence(citation, event.currentTarget)}
          >
            <span className="citation-index" aria-hidden="true">{String(index + 1).padStart(2, "0")}</span>
            <span>View source context</span>
            <code>{citation}</code>
            <span className="citation-arrow" aria-hidden="true">↗</span>
          </button>
        ))}
      </div>
      {run.invalidCitations.length > 0 && (
        <div className="invalid-citation-note" role="note">
          <strong>Needs review</strong>
          <span>{run.invalidCitations.length} returned locator{run.invalidCitations.length === 1 ? "" : "s"} could not be validated.</span>
          <div className="invalid-citation-list">
            {run.invalidCitations.map((citation) => <code key={citation}>{citation}</code>)}
          </div>
        </div>
      )}
    </section>
  );
}

function AnswerBlock({
  run,
  mode,
  onOpenEvidence,
  onOpenResearch,
}: {
  run: NormalizedUiRun;
  mode: ViewMode;
  onOpenEvidence: (citation: string, trigger: HTMLButtonElement) => void;
  onOpenResearch: () => void;
}) {
  const hasAnswer = run.answer.trim().length > 0;
  const answerFallback = run.state.kind === "NO_EVIDENCE"
    ? "No validated answer-domain evidence was found for this question."
    : run.state.kind === "FAILED"
      ? "No validated answer was produced for this run."
      : "No answer text was returned for this run.";

  return (
    <article className="answer-result" aria-labelledby="answer-result-title">
      <div className="answer-result-heading">
        <div>
          <span className="section-eyebrow">Response</span>
          <h2 id="answer-result-title">The answer</h2>
        </div>
        <StatusBadge status={run.status} />
      </div>
      <div className={hasAnswer ? "answer-copy" : "answer-copy answer-copy-muted"}>
        {hasAnswer ? run.answer : answerFallback}
      </div>

      {run.missingInformation.length > 0 && (
        <div className="missing-information" role="note">
          <div className="note-heading"><span aria-hidden="true">!</span><strong>What remains open</strong></div>
          <ul>
            {run.missingInformation.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </div>
      )}

      {run.citations.length > 0 ? (
        <EvidenceStrip run={run} onOpenEvidence={onOpenEvidence} />
      ) : (
        <div className="no-evidence-strip" role="note">
          <strong>No validated citations returned</strong>
          <span>The answer view does not invent source links when the run did not return them.</span>
        </div>
      )}

      {mode === "research" && (
        <div className="answer-boundary-note" role="note">
          <strong>Research boundary</strong>
          <span>Human correctness and faithfulness remain UNSCORED. This view reports returned runtime evidence only.</span>
        </div>
      )}

      <div className="answer-result-actions">
        <button className="secondary-action" type="button" onClick={onOpenResearch}>
          Inspect run details <span aria-hidden="true">→</span>
        </button>
      </div>
    </article>
  );
}

function RuntimeSummary({ run, onOpenResearch }: { run: NormalizedUiRun; onOpenResearch: () => void }) {
  const metrics = run.metrics;
  const entries = [
    ["Latency", metricValue(metrics?.latency_ms, " ms")],
    ["Selected", metricValue(metrics?.selected_chunks)],
    ["Citations", metricValue(metrics?.citations_valid)],
  ] as const;

  return (
    <section className="runtime-summary" aria-label="Runtime summary">
      <div className="runtime-summary-heading">
        <span>Run summary</span>
        <button className="inline-action" type="button" onClick={onOpenResearch}>Open details</button>
      </div>
      <div className="runtime-summary-grid">
        {entries.map(([label, value]) => (
          <div key={label}><span>{label}</span><strong>{value}</strong></div>
        ))}
      </div>
      <p>Measured runtime values only · answer quality is not scored here.</p>
    </section>
  );
}

export function AnswerCanvas({
  run,
  pendingQuestion,
  isRunning,
  isImporting,
  sourceNotice,
  provider,
  mode,
  sources,
  onProviderChange,
  onSubmit,
  onImport,
  onOpenEvidence,
  onOpenResearch,
  onOpenSources,
}: AnswerCanvasProps) {
  const question = pendingQuestion ?? run?.raw.query ?? null;
  const hasRun = Boolean(run || question || isRunning);

  return (
    <main className="answer-canvas" id="answer-canvas">
      <div className="answer-canvas-scroll">
        <div className="canvas-intro">
          <div>
            <span className="section-eyebrow">Ask your local corpus</span>
            <h2>{hasRun ? "Follow the evidence thread" : "Start with a focused question"}</h2>
            <p>{hasRun ? "Your question stays paired with its immutable run while you inspect the returned support." : "Import a source, ask a question, and move from the answer to the supporting chunk without losing your place."}</p>
          </div>
          <button className="canvas-sources-button" type="button" onClick={onOpenSources}>
            <span aria-hidden="true">▤</span>
            {sources.length === 0 ? "Add a source" : `${sources.length} ${sources.length === 1 ? "source" : "sources"}`}
          </button>
        </div>

        <QuestionComposer
          isRunning={isRunning}
          isImporting={isImporting}
          provider={provider}
          onProviderChange={onProviderChange}
          onSubmit={onSubmit}
          onImport={onImport}
        />

        {sourceNotice && <div className="source-notice" role="status">{sourceNotice}</div>}

        {!hasRun ? (
          <section className="canvas-ready-state" aria-label="Ready state">
            <div className="ready-marker" aria-hidden="true">01</div>
            <div>
              <strong>Ready when you are</strong>
              <p>The answer canvas stays quiet until a question is submitted. Nothing is sent outside the local runtime.</p>
            </div>
            {sources.length === 0 && <button className="secondary-action" type="button" onClick={onOpenSources}>Open corpus</button>}
          </section>
        ) : (
          <div className="run-thread" aria-live="polite" aria-busy={isRunning}>
            <section className="question-card" aria-label="Submitted question">
              <div className="question-card-label"><span className="question-card-marker" aria-hidden="true">Q</span><span>Question</span>{isRunning && <span className="question-pending-label">Working</span>}</div>
              <p>{question ?? "Question not recorded"}</p>
            </section>

            {isRunning ? (
              <LoadingProgress />
            ) : run ? (
              <>
                <RunStateBanner run={run} />
                <AnswerBlock run={run} mode={mode} onOpenEvidence={onOpenEvidence} onOpenResearch={onOpenResearch} />
                <RuntimeSummary run={run} onOpenResearch={onOpenResearch} />
              </>
            ) : (
              <section className="run-pending-empty" role="status"><strong>Preparing the run…</strong><span>The submitted question is retained while the local service responds.</span></section>
            )}
          </div>
        )}
      </div>
    </main>
  );
}

export { metricValue };
