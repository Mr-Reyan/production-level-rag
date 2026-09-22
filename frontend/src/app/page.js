"use client";

import { useEffect, useRef, useState } from "react";
import {
  useChats,
  useChatDetail,
  useUploadPdf,
  useAsk,
  useDeleteChat,
} from "@/hooks/use-rag";
import { Sidebar } from "@/components/Sidebar";
import {
  AssistantBubble,
  Composer,
  EmptyState,
  ThinkingBubble,
  UserBubble,
} from "@/components/chat";
import { MenuIcon, FileIcon } from "@/components/icons";

export default function Home() {
  const [activeChatId, setActiveChatId] = useState(null);
  const [suggestion, setSuggestion] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const scrollRef = useRef(null);

  const { data: chatsData, isLoading: chatsLoading } = useChats();
  const { data: chatDetailData, isLoading: detailLoading } = useChatDetail(activeChatId);

  const upload = useUploadPdf();
  const ask = useAsk();
  const deleteChatMutation = useDeleteChat();

  const chats = chatsData?.chats || [];
  const currentChat = chatDetailData?.chat || null;
  const currentMessages = chatDetailData?.messages || [];
  const currentDocs = chatDetailData?.documents || [];

  // Local optimistic messages state for smooth chat turns
  const [localMessages, setLocalMessages] = useState([]);

  // Sync loaded messages when switching chats
  useEffect(() => {
    if (chatDetailData?.messages) {
      setLocalMessages(
        chatDetailData.messages.map((m) => ({
          role: m.sender === "ai" ? "assistant" : "user",
          content: m.text,
          sources: [],
        }))
      );
    } else {
      setLocalMessages([]);
    }
  }, [chatDetailData?.messages, activeChatId]);

  // Auto scroll
  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [localMessages, ask.isPending]);

  function handleUpload(file, targetChatId) {
    upload.mutate(
      { file, chatId: targetChatId },
      {
        onSuccess: (data) => {
          if (data.chat_id) {
            setActiveChatId(data.chat_id);
          }
          setSidebarOpen(false);
        },
      }
    );
  }

  function handleNewChat() {
    setActiveChatId(null);
    setLocalMessages([]);
    setSidebarOpen(false);
  }

  function handleDeleteChat(chatId) {
    deleteChatMutation.mutate(chatId, {
      onSuccess: () => {
        if (activeChatId === chatId) {
          setActiveChatId(null);
          setLocalMessages([]);
        }
      },
    });
  }

  function handleSend(questionText) {
    const q = questionText?.trim();
    if (!q || !activeChatId || ask.isPending) return;

    // Add optimistic user message
    setLocalMessages((m) => [...m, { role: "user", content: q }]);

    ask.mutate(
      { chatId: activeChatId, question: q },
      {
        onSuccess: (data) => {
          setLocalMessages((m) => [
            ...m,
            {
              role: "assistant",
              content: data.answer,
              sources: data.sources || [],
            },
          ]);
        },
        onError: (err) => {
          setLocalMessages((m) => [
            ...m,
            {
              role: "assistant",
              content: `Error: ${err.message}`,
              sources: [],
            },
          ]);
        },
      }
    );
  }

  const hasChat = !!activeChatId;
  const isReady = hasChat && currentDocs.length > 0;

  return (
    <div className="flex h-dvh w-full overflow-hidden bg-neutral-50 text-neutral-900">
      <Sidebar
        chats={chats}
        activeChatId={activeChatId}
        onSelectChat={(id) => {
          setActiveChatId(id);
          setSidebarOpen(false);
        }}
        onNewChat={handleNewChat}
        onDeleteChat={handleDeleteChat}
        activeChatDocs={currentDocs}
        uploading={upload.isPending}
        onUpload={handleUpload}
        mobileOpen={sidebarOpen}
        onMobileClose={() => setSidebarOpen(false)}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Top Header */}
        <header className="flex h-14 items-center justify-between border-b border-neutral-200 bg-white px-3 sm:px-6">
          <div className="flex items-center gap-3 min-w-0">
            <button
              onClick={() => setSidebarOpen(true)}
              className="rounded-lg p-2 text-neutral-600 hover:bg-neutral-100 md:hidden"
              aria-label="Open menu"
            >
              <MenuIcon className="h-5 w-5" />
            </button>
            <div className="min-w-0">
              <div className="truncate text-sm font-semibold text-neutral-900">
                {currentChat?.title || (hasChat ? "Loading chat..." : "New Chat")}
              </div>
              <div className="truncate text-xs text-neutral-500">
                {upload.isPending
                  ? "Processing PDF & generating embeddings..."
                  : hasChat
                  ? `${currentDocs.length} document${currentDocs.length === 1 ? "" : "s"} attached`
                  : "Upload a PDF to create an isolated chat"}
              </div>
            </div>
          </div>

          {hasChat && (
            <div className="flex items-center gap-2">
              <span className="hidden sm:inline-block rounded-full bg-emerald-100 px-2.5 py-0.5 text-[11px] font-medium text-emerald-800">
                Isolated Chat
              </span>
            </div>
          )}
        </header>

        {/* Global Error Banners */}
        {upload.isError && (
          <div className="flex items-center justify-between bg-red-50 border-b border-red-200 px-4 py-2 text-xs text-red-700">
            <span>Upload Error: {upload.error?.message}</span>
            <button
              onClick={() => upload.reset()}
              className="font-medium underline hover:text-red-900"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Messages Container */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto">
          {localMessages.length === 0 && !upload.isPending ? (
            <EmptyState
              ready={isReady}
              chatTitle={currentChat?.title}
              onSelectSuggestion={(s) => setSuggestion(s)}
            />
          ) : (
            <div className="mx-auto max-w-3xl space-y-6 px-3 py-6 sm:px-6 sm:py-8">
              {localMessages.map((m, i) =>
                m.role === "user" ? (
                  <UserBubble key={i} text={m.content} />
                ) : (
                  <AssistantBubble
                    key={i}
                    text={m.content}
                    sources={m.sources}
                  />
                )
              )}
              {ask.isPending && <ThinkingBubble />}
            </div>
          )}
        </div>

        {/* Composer with Zod validation */}
        <Composer
          onSubmit={handleSend}
          disabled={!hasChat || upload.isPending}
          pending={ask.isPending}
          placeholder={
            !hasChat
              ? "Upload a PDF from the sidebar to start a chat..."
              : isReady
              ? "Ask a question about this chat's documents..."
              : "Attach a PDF to this chat first..."
          }
          externalValue={suggestion}
          onExternalChange={setSuggestion}
        />
      </div>
    </div>
  );
}