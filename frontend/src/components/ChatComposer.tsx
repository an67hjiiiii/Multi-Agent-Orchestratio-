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
    await onSubmit(trimmed);
  }

  return (
    <div className="composer-region">
      <div className="composer-hint">
        <span>Ask against your local research corpus</span>
        <span className="composer-shortcut">Enter to run · Shift + Enter for a new line</span>
      </div>
      <div className="composer">
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
        <button
          className="composer-icon-button"
          type="button"
          aria-label="Add a text source"
          title="Add a text source"
          disabled={isImporting}
          onClick={() => fileRef.current?.click()}
        >
          {isImporting ? "…" : "＋"}
        </button>
        <textarea
          aria-label="Research question"
          value={message}
          rows={1}
          placeholder="Ask a question about the current corpus…"
          onChange={(event) => setMessage(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void submit();
            }
          }}
        />
        <button className="send-button" type="button" disabled={isRunning || !message.trim()} onClick={() => void submit()}>
          {isRunning ? "Running…" : "Run"}
          <span aria-hidden="true">↗</span>
        </button>
      </div>
    </div>
  );
}
