import { useCallback, useEffect, useState } from "react";
import { conversationApi } from "./api";
import type { Conversation } from "../../types/api";

interface ResearchControls {
  startNewRun: () => void;
  selectRun: (runId: string) => Promise<void>;
}

export interface ConversationWorkspaceState {
  conversations: Conversation[];
  activeConversation: Conversation | null;
  conversationError: string | null;
  conversationBusy: boolean;
  conversationHistoryLoading: boolean;
  conversationHistoryError: string | null;
  retryConversationHistory: () => Promise<void>;
  retryOpenConversation: () => Promise<void>;
  retryableConversationId: string | null;
  startNewConversation: () => Promise<void>;
  openConversation: (conversationId: string) => Promise<void>;
  submitQuestion: (message: string) => Promise<void>;
  dismissConversationError: () => void;
  reset: () => void;
}

interface UseConversationWorkspaceOptions {
  sessionKey: string | null;
  provider: string | null;
  research: ResearchControls;
  onNavigateToResearch: () => void;
}

/** Owns conversation loading and turn orchestration for the research shell. */
export function useConversationWorkspace({
  sessionKey,
  provider,
  research,
  onNavigateToResearch,
}: UseConversationWorkspaceOptions): ConversationWorkspaceState {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversation, setActiveConversation] = useState<Conversation | null>(null);
  const [conversationError, setConversationError] = useState<string | null>(null);
  const [conversationBusy, setConversationBusy] = useState(false);
  const [conversationHistoryLoading, setConversationHistoryLoading] = useState(false);
  const [conversationHistoryError, setConversationHistoryError] = useState<string | null>(null);
  const [retryableConversationId, setRetryableConversationId] = useState<string | null>(null);

  const loadConversationHistory = useCallback(async () => {
    if (!sessionKey) return;
    setConversationHistoryLoading(true);
    setConversationHistoryError(null);
    try {
      const result = await conversationApi.listConversations();
      setConversations(result.conversations ?? []);
    } catch (cause) {
      setConversationHistoryError(cause instanceof Error ? cause.message : "Conversation history is unavailable");
    } finally {
      setConversationHistoryLoading(false);
    }
  }, [sessionKey]);

  useEffect(() => {
    if (!sessionKey) {
      setConversations([]);
      setActiveConversation(null);
      setConversationHistoryLoading(false);
      setConversationHistoryError(null);
      return;
    }
    void loadConversationHistory();
  }, [loadConversationHistory, sessionKey]);

  async function startNewConversation() {
    research.startNewRun();
    setActiveConversation(null);
    onNavigateToResearch();
    setConversationError(null);
    setRetryableConversationId(null);
    try {
      const conversation = await conversationApi.createConversation();
      setActiveConversation(conversation);
      setConversations((current) => [conversation, ...current]);
    } catch (cause) {
      const detail = cause instanceof Error ? cause.message : "Unable to start a conversation";
      setConversationError(`${detail} Your question is still available in the composer; try again when the local service is ready.`);
    }
  }

  async function openConversation(conversationId: string) {
    setConversationBusy(true);
    setConversationError(null);
    setRetryableConversationId(null);
    try {
      const conversation = await conversationApi.getConversation(conversationId);
      setActiveConversation(conversation);
      onNavigateToResearch();
      research.startNewRun();
      const latestRun = [...conversation.messages].reverse().find((message) => message.run_id);
      if (latestRun?.run_id) await research.selectRun(latestRun.run_id);
    } catch (cause) {
      const detail = cause instanceof Error ? cause.message : "Unable to reopen this conversation";
      setConversationError(`${detail} Check the local service, then try again.`);
      setRetryableConversationId(conversationId);
    } finally {
      setConversationBusy(false);
    }
  }

  async function retryOpenConversation() {
    if (retryableConversationId) await openConversation(retryableConversationId);
  }

  async function submitQuestion(message: string) {
    onNavigateToResearch();
    setConversationBusy(true);
    setConversationError(null);
    setRetryableConversationId(null);
    try {
      let conversation = activeConversation;
      if (!conversation) {
        conversation = await conversationApi.createConversation();
        setActiveConversation(conversation);
        setConversations((current) => [conversation as Conversation, ...current]);
      }
      const response = await conversationApi.sendConversationMessage(conversation.conversation_id, {
        message,
        condition: "A",
        provider: provider ?? undefined,
      });
      setActiveConversation(response.conversation);
      setConversations((current) => current.map((item) => item.conversation_id === response.conversation.conversation_id ? response.conversation : item));
      if (response.run?.run_id) await research.selectRun(response.run.run_id);
    } catch (cause) {
      const detail = cause instanceof Error ? cause.message : "Unable to continue this conversation";
      setConversationError(`${detail} Your question is still available in the composer; try again when the local service is ready.`);
      throw cause;
    } finally {
      setConversationBusy(false);
    }
  }

  return {
    conversations,
    activeConversation,
    conversationError,
    conversationBusy,
    conversationHistoryLoading,
    conversationHistoryError,
    retryConversationHistory: loadConversationHistory,
    retryOpenConversation,
    retryableConversationId,
    startNewConversation,
    openConversation,
    submitQuestion,
    dismissConversationError: () => setConversationError(null),
    reset: () => {
      setConversations([]);
      setActiveConversation(null);
      setConversationError(null);
      setConversationBusy(false);
      setConversationHistoryLoading(false);
      setConversationHistoryError(null);
      setRetryableConversationId(null);
    },
  };
}
