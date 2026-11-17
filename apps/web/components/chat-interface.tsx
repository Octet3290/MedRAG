"use client";

import { useEffect, useRef, useState } from "react";
import {
  CitationItem,
  ConversationDetail,
  ConversationSummary,
  createConversation,
  deleteConversation,
  getConversation,
  listConversations,
  sendChatMessage,
} from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

interface ChatInterfaceProps {
  kbId: string;
  kbName: string;
  documentCount: number;
}

export function ChatInterface({ kbId, kbName, documentCount }: ChatInterfaceProps) {
  const { token } = useAuth();
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [activeConversation, setActiveConversation] = useState<ConversationDetail | null>(null);

  const [loadingList, setLoadingList] = useState(false);
  const [loadingConv, setLoadingConv] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [inputMessage, setInputMessage] = useState("");
  const [selectedCitation, setSelectedCitation] = useState<CitationItem | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to latest message
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [activeConversation?.messages, sending]);

  // Load conversation list
  const loadConversations = async () => {
    if (!token) return;
    try {
      setLoadingList(true);
      setError(null);
      const res = await listConversations(token, kbId);
      setConversations(res.items);
      if (res.items.length > 0 && !activeConvId) {
        setActiveConvId(res.items[0].id);
      }
    } catch (err: unknown) {
      if (err instanceof Error) setError(err.message);
    } finally {
      setLoadingList(false);
    }
  };

  useEffect(() => {
    loadConversations();
  }, [kbId, token]);

  // Load active conversation details when activeConvId changes
  useEffect(() => {
    if (!token || !activeConvId) {
      setActiveConversation(null);
      return;
    }

    const loadActiveConv = async () => {
      try {
        setLoadingConv(true);
        setError(null);
        setSelectedCitation(null);
        const detail = await getConversation(token, activeConvId);
        setActiveConversation(detail);
      } catch (err: unknown) {
        if (err instanceof Error) setError(err.message);
      } finally {
        setLoadingConv(false);
      }
    };

    loadActiveConv();
  }, [activeConvId, token]);

  const handleCreateNewChat = async () => {
    if (!token || sending) return;
    try {
      setError(null);
      const newConv = await createConversation(token, kbId, "New Consultation");
      await loadConversations();
      setActiveConvId(newConv.id);
      setActiveConversation(newConv);
    } catch (err: unknown) {
      if (err instanceof Error) setError(err.message);
    }
  };

  const handleDeleteConversation = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!token || !confirm("Delete this conversation?")) return;
    try {
      setError(null);
      await deleteConversation(token, id);
      if (activeConvId === id) {
        setActiveConvId(null);
        setActiveConversation(null);
      }
      await loadConversations();
    } catch (err: unknown) {
      if (err instanceof Error) setError(err.message);
    }
  };

  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputMessage.trim() || !token || sending) return;

    let targetConvId = activeConvId;

    try {
      setSending(true);
      setError(null);
      setSelectedCitation(null);

      // If no active conversation exists, create one first
      if (!targetConvId) {
        const newConv = await createConversation(token, kbId, "New Consultation");
        targetConvId = newConv.id;
        setActiveConvId(newConv.id);
        setActiveConversation(newConv);
      }

      const userText = inputMessage.trim();
      setInputMessage("");

      // Optimistically append user message to UI
      const optimisticUserMsg = {
        id: "temp-user-" + Date.now(),
        conversation_id: targetConvId,
        role: "user" as const,
        content: userText,
        citations: [],
        model_metadata: {},
        created_at: new Date().toISOString(),
      };

      setActiveConversation((prev) =>
        prev
          ? {
              ...prev,
              messages: [...prev.messages, optimisticUserMsg],
            }
          : null
      );

      const turn = await sendChatMessage(token, targetConvId, userText);

      // Replace optimistic message and append assistant message
      setActiveConversation((prev) => {
        if (!prev) return null;
        const filtered = prev.messages.filter((m) => m.id !== optimisticUserMsg.id);
        return {
          ...prev,
          messages: [...filtered, turn.user_message, turn.assistant_message],
        };
      });

      // Refresh list in background to update title & message counts
      loadConversations();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Failed to send message");
      }
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="flex flex-col lg:flex-row gap-6 h-[720px] max-h-[80vh]">
      {/* Left Sidebar: Conversation Sessions */}
      <div className="w-full lg:w-72 flex flex-col rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-sm overflow-hidden flex-shrink-0">
        {/* Sidebar Header */}
        <div className="p-3.5 border-b border-zinc-100 dark:border-zinc-800 flex items-center justify-between">
          <span className="text-xs font-semibold text-zinc-900 dark:text-zinc-100">
            Chat Threads
          </span>
          <button
            onClick={handleCreateNewChat}
            className="px-2.5 py-1 text-xs font-semibold rounded-md bg-indigo-600 text-white hover:bg-indigo-700 transition-colors shadow-sm flex items-center gap-1"
          >
            <span>+</span> New Chat
          </button>
        </div>

        {/* Conversation List */}
        <div className="flex-1 overflow-y-auto divide-y divide-zinc-100 dark:divide-zinc-800 p-1">
          {loadingList ? (
            <div className="p-4 text-center text-xs text-zinc-400 animate-pulse">
              Loading chat sessions...
            </div>
          ) : conversations.length === 0 ? (
            <div className="p-6 text-center text-xs text-zinc-400">
              No conversations yet. Click <strong>+ New Chat</strong> to start your first session.
            </div>
          ) : (
            conversations.map((c) => {
              const isActive = activeConvId === c.id;
              return (
                <div
                  key={c.id}
                  onClick={() => setActiveConvId(c.id)}
                  className={`group p-3 rounded-lg cursor-pointer transition-all flex items-start justify-between gap-2 text-left ${
                    isActive
                      ? "bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-900"
                      : "hover:bg-zinc-50 dark:hover:bg-zinc-800/60"
                  }`}
                >
                  <div className="flex flex-col gap-0.5 overflow-hidden">
                    <span
                      className={`text-xs font-medium truncate ${
                        isActive
                          ? "text-indigo-900 dark:text-indigo-200"
                          : "text-zinc-800 dark:text-zinc-200"
                      }`}
                    >
                      {c.title}
                    </span>
                    <span className="text-[10px] text-zinc-400">
                      {c.message_count} messages • {new Date(c.updated_at).toLocaleDateString()}
                    </span>
                  </div>
                  <button
                    onClick={(e) => handleDeleteConversation(e, c.id)}
                    className="opacity-0 group-hover:opacity-100 text-zinc-400 hover:text-rose-600 p-1 rounded transition-opacity"
                    title="Delete Chat"
                  >
                    ✕
                  </button>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Right Column: Chat Thread & Input */}
      <div className="flex-1 flex flex-col rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-sm overflow-hidden">
        {/* Chat Thread Header */}
        <div className="px-5 py-3 border-b border-zinc-100 dark:border-zinc-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 truncate max-w-md">
              {activeConversation?.title || "AI Knowledge Consultation"}
            </h3>
          </div>
          <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-500">
            {documentCount} docs indexed
          </span>
        </div>

        {/* Messages Stream */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {documentCount === 0 && (
            <div className="p-3.5 rounded-lg bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-300 text-xs">
              ⚠️ No documents indexed in this knowledge base. Upload guidelines or papers in the{" "}
              <strong>Documents</strong> tab to ground responses.
            </div>
          )}

          {loadingConv ? (
            <div className="py-12 text-center text-xs text-zinc-400 animate-pulse">
              Loading conversation thread...
            </div>
          ) : !activeConversation || activeConversation.messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-8 gap-3 my-auto">
              <div className="w-12 h-12 rounded-full bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 flex items-center justify-center font-bold text-xl">
                💬
              </div>
              <h4 className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">
                Multi-Turn Medical Knowledge Assistant
              </h4>
              <p className="text-xs text-zinc-500 max-w-sm">
                Ask initial questions and follow up naturally with context awareness. Pronouns and
                follow-ups are automatically reformulated against indexed documentation.
              </p>
            </div>
          ) : (
            activeConversation.messages.map((m) => {
              const isUser = m.role === "user";
              return (
                <div
                  key={m.id}
                  className={`flex flex-col gap-1.5 ${isUser ? "items-end" : "items-start"}`}
                >
                  <div
                    className={`max-w-[85%] rounded-2xl px-4 py-3 text-xs leading-relaxed shadow-sm ${
                      isUser
                        ? "bg-indigo-600 text-white rounded-br-none"
                        : "bg-zinc-50 dark:bg-zinc-800/80 border border-zinc-200 dark:border-zinc-700/80 text-zinc-900 dark:text-zinc-100 rounded-bl-none"
                    }`}
                  >
                    <div className="whitespace-pre-wrap">{m.content}</div>

                    {/* Citations on Assistant Messages */}
                    {!isUser && m.citations && m.citations.length > 0 && (
                      <div className="mt-3 pt-2.5 border-t border-zinc-200 dark:border-zinc-700 flex flex-col gap-1.5">
                        <span className="text-[10px] font-semibold text-zinc-500 dark:text-zinc-400">
                          Verified Citations:
                        </span>
                        <div className="flex flex-wrap gap-1.5">
                          {m.citations.map((c, idx) => (
                            <button
                              key={idx}
                              onClick={() => setSelectedCitation(c)}
                              className="px-2 py-0.5 rounded text-[10px] font-mono bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 text-indigo-600 dark:text-indigo-400 hover:border-indigo-400 transition-colors flex items-center gap-1"
                            >
                              <span>📄 {c.document_title}</span>
                              <span className="text-zinc-400">P.{c.page_number ?? "N/A"}</span>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                  <span className="text-[10px] text-zinc-400 px-1 font-mono">
                    {new Date(m.created_at).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </div>
              );
            })
          )}

          {/* Typing Indicator */}
          {sending && (
            <div className="flex items-start gap-2">
              <div className="bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-2xl rounded-bl-none px-4 py-2.5 text-xs text-zinc-500 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-bounce" />
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-bounce [animation-delay:0.2s]" />
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-bounce [animation-delay:0.4s]" />
                <span className="ml-1 text-[11px]">Reformulating query & searching vector chunks...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Selected Citation Drawer Preview */}
        {selectedCitation && (
          <div className="p-3 bg-indigo-50/70 dark:bg-indigo-950/40 border-t border-indigo-200 dark:border-indigo-900 flex items-start justify-between gap-3 text-xs">
            <div className="flex flex-col gap-1 overflow-hidden">
              <span className="font-semibold text-indigo-900 dark:text-indigo-200">
                🔍 Source Passage: {selectedCitation.document_title} (Page {selectedCitation.page_number ?? "N/A"})
              </span>
              <p className="text-[11px] text-zinc-700 dark:text-zinc-300 font-mono bg-white dark:bg-zinc-900 p-2 rounded border border-indigo-100 dark:border-indigo-900 line-clamp-2">
                {selectedCitation.excerpt}
              </p>
            </div>
            <button
              onClick={() => setSelectedCitation(null)}
              className="text-xs text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200"
            >
              ✕
            </button>
          </div>
        )}

        {/* Input Bar */}
        <div className="p-3 border-t border-zinc-100 dark:border-zinc-800 bg-white dark:bg-zinc-900">
          {error && (
            <div className="mb-2 p-2 rounded text-xs bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-rose-700 dark:text-rose-300">
              {error}
            </div>
          )}

          <form onSubmit={handleSendMessage} className="flex items-end gap-2">
            <textarea
              rows={2}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question or follow up on previous answers..."
              disabled={sending || documentCount === 0}
              className="flex-1 px-3.5 py-2 text-xs rounded-xl border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 placeholder:text-zinc-400 text-zinc-900 dark:text-zinc-100 resize-none"
            />
            <button
              type="submit"
              disabled={sending || !inputMessage.trim() || documentCount === 0}
              className="px-4 py-2.5 rounded-xl bg-indigo-600 text-white text-xs font-semibold hover:bg-indigo-700 disabled:opacity-50 transition-colors shadow-sm flex-shrink-0"
            >
              Send
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
