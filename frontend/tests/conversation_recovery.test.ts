import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { HistoryView } from "../src/components/ProductViews";

const baseProps = {
  conversations: [],
  onNewConversation: vi.fn(),
  onSelectConversation: vi.fn(),
  history: [],
  onSelectRun: vi.fn(),
};

describe("conversation and history recovery UI", () => {
  it("shows a loading state while the local history store is being checked", () => {
    const markup = renderToStaticMarkup(createElement(HistoryView, {
      ...baseProps,
      conversationHistoryLoading: true,
    }));

    expect(markup).toContain("Loading conversation history");
    expect(markup).toContain('aria-busy="true"');
    expect(markup).not.toContain("No conversations yet.");
  });

  it("keeps history recovery explicit and actionable after a list failure", () => {
    const markup = renderToStaticMarkup(createElement(HistoryView, {
      ...baseProps,
      conversationHistoryError: "The local conversation store is unavailable.",
      onRetryConversationHistory: vi.fn(),
    }));

    expect(markup).toContain("Conversation history could not be loaded.");
    expect(markup).toContain("The local conversation store is unavailable.");
    expect(markup).toContain("Try again");
    expect(markup).toContain('role="alert"');
  });
});
