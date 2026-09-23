import { api } from "../../lib/api";

/** Conversation routes owned by the conversation feature. */
export const conversationApi = {
  listConversations: api.listConversations,
  createConversation: api.createConversation,
  getConversation: api.getConversation,
  sendConversationMessage: api.sendConversationMessage,
};
