import type { RunRecord } from "../types/api";
import { ChatComposer } from "./ChatComposer";

interface ChatPanelProps {
  run: RunRecord | null;
  isRunning: boolean;
  isImporting: boolean;
  sourceNotice: string | null;
  onSubmit: (message: string) => Promise<void>;
  onImport: (file: File) => Promise<void>;
}
export function ChatPanel({
  run,
  isRunning,
  isImporting,
  sourceNotice,
  onSubmit,
  onImport,
}: ChatPanelProps) {
  const citations = Array.from(
    new Set((run?.task_results ?? []).flatMap((result) => result.citations ?? [])),
  );

  return (
    <main className="chat-panel">
      <div className="chat-header">
        <div>
          <p className="eyebrow">M0 research console</p>
          <h1>Explore your evidence</h1>
        </div>
        <div className="chat-header-note">
          <span className="header-pulse" aria-hidden="true" />
          <span>Runs stay on this machine</span>
        </div>
      </div>

      <div className="conversation" aria-live="polite">
        {!run ? (
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
              <span className="message-label">You</span>
              <p>{run.query || "Research question"}</p>
            </div>
            <div className="answer-block">
              <div className="answer-heading">
                <span className="answer-avatar" aria-hidden="true">LR</span>
                <span className="message-label">Research answer</span>
              </div>
              <p className="answer-copy">{run.answer || "No answer was returned for this run."}</p>
              {citations.length > 0 && (
                <div className="answer-citations">
                  <span className="citation-label">Cited evidence</span>
                  {citations.map((citation) => <span className="citation-chip" key={citation}>{citation}</span>)}
                </div>
              )}
            </div>
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
