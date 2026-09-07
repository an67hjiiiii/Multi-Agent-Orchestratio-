import { useRef, useState } from "react";

interface QuestionComposerProps {
  isRunning: boolean;
  isImporting: boolean;
  provider: string;
  onProviderChange: (provider: string) => void;
  onSubmit: (message: string) => Promise<void>;
  onImport: (file: File) => Promise<void>;
}
export function QuestionComposer({
  isRunning,
  isImporting,
  provider,
  onProviderChange,
  onSubmit,
  onImport,
}: QuestionComposerProps) {
  const [message, setMessage] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  async function submit() {
    const trimmed = message.trim();
    if (!trimmed || isRunning) return;

    // Keep the submitted question visible until the request resolves. This
    // avoids clearing the user's draft while a local run is still pending.
    try {
      await onSubmit(trimmed);
      setMessage("");
    } catch {
      // The shell owns the safe error state and keeps the draft available.
    }
  }

  return (
    <section className="question-composer" aria-labelledby="question-composer-title">
      <div className="composer-heading-row">
        <div>
          <span className="section-eyebrow">Ask the corpus</span>
          <h2 id="question-composer-title">What do you want to verify?</h2>
        </div>
        <details className="run-options">
          <summary>Run options</summary>
          <div className="run-options-popover">
            <label htmlFor="composer-provider">Provider</label>
            <select
              id="composer-provider"
              value={provider}
              disabled={isRunning}
              onChange={(event) => onProviderChange(event.target.value)}
            >
              <option value="fake">Fake · wiring/test only</option>
              <option value="ollama">Local Ollama</option>
            </select>
            <div className="run-option-locked"><span>Condition</span><strong>A</strong><small>Locked in M0</small></div>
          </div>
        </details>
      </div>
      <div className="composer-boundary-note">
        <span className="boundary-dot" aria-hidden="true" />
        <span>Questions stay on this machine. Import UTF-8 text or code to expand the corpus.</span>
      </div>
      <form
        className="question-form"
        aria-busy={isRunning}
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
      >
        <input
          ref={fileRef}
          className="visually-hidden"
          id="source-file"
          type="file"
          accept=".txt,.md,.markdown,.py,.js,.ts,.tsx,.json,.yaml,.yml,.csv"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) void onImport(file);
            event.target.value = "";
          }}
        />
        <label className="visually-hidden" htmlFor="source-file">Add a UTF-8 source file</label>
        <button
          className="composer-tool-button"
          type="button"
          aria-label="Add a UTF-8 source file"
          title="Add a UTF-8 source file"
          disabled={isImporting}
          onClick={() => fileRef.current?.click()}
        >
          <span aria-hidden="true">＋</span>
          <span className="composer-tool-label">Source</span>
        </button>
        <label className="visually-hidden" htmlFor="research-question">Research question</label>
        <textarea
          id="research-question"
          value={message}
          rows={2}
          placeholder="Ask a focused question about the current corpus…"
          disabled={isRunning}
          aria-describedby="question-help"
          onChange={(event) => setMessage(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void submit();
            }
          }}
        />
        <button className="question-submit" type="submit" disabled={isRunning || !message.trim()}>
          <span>{isRunning ? "Working" : "Ask"}</span>
          <span aria-hidden="true">↗</span>
        </button>
      </form>
      <div className="composer-help" id="question-help">
        <span>{isImporting ? "Adding source to the corpus…" : "Enter to ask · Shift + Enter for a new line"}</span>
        <span>UTF-8 · text/code · 2 MB</span>
      </div>
    </section>
  );
}
