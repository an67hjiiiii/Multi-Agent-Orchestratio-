import { useRef, useState } from "react";

interface ChatComposerProps {
  isRunning: boolean;
  isImporting: boolean;
  onSubmit: (message: string) => Promise<void>;
  onImport: (file: File) => Promise<void>;
}
export function ChatComposer({ isRunning, isImporting, onSubmit, onImport }: ChatComposerProps) {
  const [message, setMessage] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  async function submit() {
    const trimmed = message.trim();
    if (!trimmed || isRunning) return;
    setMessage("");
    try {
      await onSubmit(trimmed);
    } catch {
      // The app-level alert owns the failed run state; keep the composer settled.
    }
  }

  return (
    <div className="composer-region">
      <div className="composer-hint" id="composer-help">
        <span>Ask against your local research corpus</span>
        <span className="composer-shortcut">Enter to run · Shift + Enter for a new line</span>
      </div>
      <form
        className="composer"
        aria-busy={isRunning}
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
      >
        <input
          ref={fileRef}
          className="visually-hidden"
          type="file"
          accept=".txt,.md,.markdown,.pdf,.py,.js,.ts,.tsx,.json,.yaml,.yml,.csv"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) void onImport(file);
            event.target.value = "";
          }}
        />
        <button
          className="composer-icon-button"
          type="button"
          aria-label="Add a text source or text-only PDF"
          title="Add a text source or text-only PDF"
          disabled={isImporting}
          onClick={() => fileRef.current?.click()}
        >
          {isImporting ? "…" : "＋"}
        </button>
        <textarea
          aria-label="Research question"
          aria-describedby="composer-help"
          value={message}
          rows={1}
          placeholder="Ask a question about the current corpus…"
          disabled={isRunning}
          onChange={(event) => setMessage(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void submit();
            }
          }}
        />
        <button className="send-button" type="submit" disabled={isRunning || !message.trim()}>
          {isRunning ? "Running…" : "Run"}
          <span aria-hidden="true">↗</span>
        </button>
      </form>
    </div>
  );
}
