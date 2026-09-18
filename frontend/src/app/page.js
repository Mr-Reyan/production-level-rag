"use client";

import { useEffect, useRef, useState } from "react";
import { useUploadPdf, useAsk } from "@/hooks/use-rag";
import { Sidebar } from "@/components/Sidebar";
import {
  AssistantBubble,
  Composer,
  EmptyState,
  ThinkingBubble,
  UserBubble,
} from "@/components/chat";
import { MenuIcon } from "@/components/icons";

export default function Home() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [pdfName, setPdfName] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const scrollRef = useRef(null);

  const upload = useUploadPdf();
  const ask = useAsk();

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, ask.isPending]);

  function handleUpload(file) {
    setPdfName(file.name);
    upload.mutate(file, {
      onSuccess: () => {
        setMessages([]);
        setSidebarOpen(false);
      },
    });
  }

  function handleReset() {
    setPdfName(null);
    setMessages([]);
    upload.reset();
  }

  function handleSend() {
    const q = input.trim();
    if (!q || ask.isPending) return;

    setMessages((m) => [...m, { role: "user", content: q }]);
    setInput("");

    ask.mutate(q, {
      onSuccess: (data) => {
        setMessages((m) => [
          ...m,
          { role: "assistant", content: data.answer, sources: data.sources || [] },
        ]);
      },
      onError: (err) => {
        setMessages((m) => [
          ...m,
          { role: "assistant", content: `Error: ${err.message}`, sources: [] },
        ]);
      },
    });
  }

  const ready = !!pdfName && upload.isSuccess;
  const indexed = upload.data?.chunks ?? 0;

  return (
    <div className="flex h-dvh w-full overflow-hidden">
      <Sidebar
        pdfName={pdfName}
        chunkCount={indexed}
        uploading={upload.isPending}
        onUpload={handleUpload}
        onReset={handleReset}
        mobileOpen={sidebarOpen}
        onMobileClose={() => setSidebarOpen(false)}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Top bar */}
        <header className="flex h-14 items-center gap-3 border-b border-neutral-200 bg-white px-3 sm:px-6">
          <button
            onClick={() => setSidebarOpen(true)}
            className="rounded-lg p-2 text-neutral-600 hover:bg-neutral-100 md:hidden"
            aria-label="Open menu"
          >
            <MenuIcon className="h-5 w-5" />
          </button>
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-medium">
              {pdfName ?? "No document"}
            </div>
            <div className="truncate text-xs text-neutral-500">
              {upload.isPending
                ? "Indexing document…"
                : upload.isError
                ? `Upload failed: ${upload.error?.message || "Unknown error"}`
                : ready
                ? `${indexed} chunks indexed`
                : "Upload a PDF to start"}
            </div>
          </div>
        </header>

        {/* Upload error banner if any */}
        {upload.isError && (
          <div className="bg-red-50 border-b border-red-200 px-4 py-2 text-xs text-red-700 flex items-center justify-between">
            <span>Upload error: {upload.error?.message}</span>
            <button
              onClick={() => upload.reset()}
              className="text-xs font-semibold text-red-800 underline hover:text-red-900"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Messages */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto bg-neutral-50">
          {messages.length === 0 && !upload.isPending ? (
            <EmptyState ready={ready} onSelectSuggestion={(s) => setInput(s)} />
          ) : (
            <div className="mx-auto max-w-3xl space-y-6 px-3 py-6 sm:px-6 sm:py-8">
              {messages.map((m, i) =>
                m.role === "user" ? (
                  <UserBubble key={i} text={m.content} />
                ) : (
                  <AssistantBubble key={i} text={m.content} sources={m.sources} />
                )
              )}
              {ask.isPending && <ThinkingBubble />}
            </div>
          )}
        </div>

        {/* Composer */}
        <Composer
          value={input}
          onChange={setInput}
          onSubmit={handleSend}
          disabled={!ready}
          pending={ask.isPending}
          placeholder={ready ? "Ask about this document…" : "Upload a PDF first"}
        />
      </div>
    </div>
  );
}