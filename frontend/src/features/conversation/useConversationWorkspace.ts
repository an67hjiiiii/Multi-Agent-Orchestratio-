import { useEffect, useState } from "react";
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
  startNewConversation: () => Promise<void>;
  openConversation: (conversationId: string) => Promise<void>;
  submitQuestion: (message: string) => Promise<void>;
  dismissConversationError: () => void;
  reset: () => void;
}

interface UseConversationWorkspaceOptions {
  sessionKey: string | null;
  provider: string;
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

  useEffect(() => {
    if (!sessionKey) {
      setConversations([]);
      setActiveConversation(null);
      return;
    }
    let cancelled = false;
    setConversationError(null);
    void conversationApi.listConversations()
      .then((result) => {
        if (!cancelled) setConversations(result.conversations ?? []);
      })
      .catch((cause) => {
        if (!cancelled) setConversationError(cause instanceof Error ? cause.message : "Conversation history is unavailable");
      });
    return () => { cancelled = true; };
  }, [sessionKey]);

  async function startNewConversation() {
    research.startNewRun();
    setActiveConversation(null);
    onNavigateToResearch();
    setConversationError(null);
    try {
      const conversation = await conversationApi.createConversation();
      setActiveConversation(conversation);
      setConversations((current) => [conversation, ...current]);
    } catch (cause) {
      setConversationError(cause instanceof Error ? cause.message : "Unable to start a conversation");
    }
  }

  async function openConversation(conversationId: string) {
    setConversationBusy(true);
    setConversationError(null);
    try {
      const conversation = await conversationApi.getConversation(conversationId);
      setActiveConversation(conversation);
      onNavigateToResearch();
      research.startNewRun();
      const latestRun = [...conversation.messages].reverse().find((message) => message.run_id);
      if (latestRun?.run_id) await research.selectRun(latestRun.run_id);
    } catch (cause) {
      setConversationError(cause instanceof Error ? cause.message : "Unable to reopen this conversation");
    } finally {
      setConversationBusy(false);
    }
  }

  async function submitQuestion(message: string) {
    onNavigateToResearch();
    setConversationBusy(true);
    setConversationError(null);
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
        provider,
      });
      setActiveConversation(response.conversation);
      setConversations((current) => current.map((item) => item.conversation_id === response.conversation.conversation_id ? response.conversation : item));
      if (response.run?.run_id) await research.selectRun(response.run.run_id);
    } catch (cause) {
      setConversationError(cause instanceof Error ? cause.message : "Unable to continue this conversation");
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
    startNewConversation,
    openConversation,
    submitQuestion,
    dismissConversationError: () => setConversationError(null),
    reset: () => {
      setConversations([]);
      setActiveConversation(null);
      setConversationError(null);
      setConversationBusy(false);
    },
  };
}
