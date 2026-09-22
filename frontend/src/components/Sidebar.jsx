"use client";

import { useState } from "react";
import { FileIcon, XIcon, SparkIcon } from "./icons";
import { pdfUploadSchema } from "../lib/validations";

export function Sidebar({
  chats = [],
  activeChatId,
  onSelectChat,
  onNewChat,
  onDeleteChat,
  activeChatDocs = [],
  uploading,
  onUpload,
  mobileOpen,
  onMobileClose,
}) {
  const [uploadError, setUploadError] = useState(null);

  function handleFileSelected(file, targetChatId) {
    setUploadError(null);
    const result = pdfUploadSchema.safeParse({ file, chatId: targetChatId });
    if (!result.success) {
      const errorMsg = result.error.errors[0]?.message || "Invalid PDF file";
      setUploadError(errorMsg);
      return;
    }
    onUpload(file, targetChatId);
  }

  return (
    <>
      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          onClick={onMobileClose}
          className="fixed inset-0 z-30 bg-neutral-900/40 md:hidden"
        />
      )}

      <aside
        className={`
          fixed inset-y-0 left-0 z-40 flex w-80 flex-col border-r border-neutral-200 bg-white
          transition-transform md:static md:translate-x-0
          ${mobileOpen ? "translate-x-0" : "-translate-x-full"}
        `}
      >
        {/* Brand & New Chat */}
        <div className="flex flex-col gap-3 border-b border-neutral-200 p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-neutral-900 text-white">
                <SparkIcon className="h-4 w-4" />
              </div>
              <div className="leading-tight">
                <div className="text-sm font-semibold">Doc Q&A</div>
                <div className="text-xs text-neutral-500">Chat-Isolated RAG</div>
              </div>
            </div>
            <button
              onClick={onMobileClose}
              className="rounded-md p-1.5 text-neutral-500 hover:bg-neutral-100 md:hidden"
              aria-label="Close menu"
            >
              <XIcon className="h-4 w-4" />
            </button>
          </div>

          <button
            onClick={onNewChat}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-neutral-900 px-4 py-2.5 text-xs font-semibold text-white transition hover:bg-neutral-800"
          >
            <span>+</span>
            <span>New Chat</span>
          </button>
        </div>

        {/* Chats History List */}
        <div className="flex-1 overflow-y-auto px-3 py-3">
          <div className="mb-2 px-2 text-[11px] font-semibold uppercase tracking-wider text-neutral-400">
            Recent Chats ({chats.length})
          </div>

          {chats.length === 0 ? (
            <div className="rounded-xl border border-dashed border-neutral-200 p-4 text-center text-xs text-neutral-400">
              No chats yet. Upload a PDF to start one!
            </div>
          ) : (
            <div className="space-y-1">
              {chats.map((chat) => {
                const isActive = chat.id === activeChatId;
                return (
                  <div
                    key={chat.id}
                    onClick={() => onSelectChat(chat.id)}
                    className={`
                      group flex cursor-pointer items-center justify-between rounded-xl px-3 py-2.5 text-xs transition
                      ${
                        isActive
                          ? "bg-neutral-900 text-white font-medium"
                          : "text-neutral-700 hover:bg-neutral-100"
                      }
                    `}
                  >
                    <div className="min-w-0 flex-1 pr-2">
                      <p className="truncate">{chat.title || "Untitled Chat"}</p>
                      <p
                        className={`text-[10px] ${
                          isActive ? "text-neutral-300" : "text-neutral-400"
                        }`}
                      >
                        {chat.message_count} messages
                      </p>
                    </div>

                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        if (confirm(`Delete chat "${chat.title}"?`)) {
                          onDeleteChat(chat.id);
                        }
                      }}
                      className={`
                        rounded p-1 transition opacity-0 group-hover:opacity-100
                        ${
                          isActive
                            ? "text-neutral-300 hover:bg-neutral-800 hover:text-white"
                            : "text-neutral-400 hover:bg-neutral-200 hover:text-red-600"
                        }
                      `}
                      title="Delete chat"
                    >
                      <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
                      </svg>
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Upload section */}
        <div className="border-t border-neutral-200 bg-neutral-50/50 p-4">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-neutral-500">
              {activeChatId ? "In-Chat Upload" : "Start New Chat"}
            </span>
            {activeChatId && activeChatDocs.length > 0 && (
              <span className="text-[10px] text-neutral-400">
                {activeChatDocs.length} doc{activeChatDocs.length === 1 ? "" : "s"}
              </span>
            )}
          </div>

          {uploadError && (
            <div className="mb-2 rounded-lg bg-red-50 p-2 text-[11px] text-red-600">
              {uploadError}
            </div>
          )}

          {/* Active chat docs list */}
          {activeChatId && activeChatDocs.length > 0 && (
            <div className="mb-3 space-y-1.5">
              {activeChatDocs.map((doc, i) => (
                <div
                  key={doc.source_id || i}
                  className="flex items-center gap-2 rounded-lg border border-neutral-200 bg-white px-2.5 py-1.5 text-xs text-neutral-700"
                >
                  <FileIcon className="h-3.5 w-3.5 shrink-0 text-neutral-500" />
                  <span className="truncate">{doc.title}</span>
                </div>
              ))}
            </div>
          )}

          <UploadCard
            uploading={uploading}
            label={
              activeChatId
                ? "Attach PDF to this chat"
                : "Upload PDF to create chat"
            }
            onUpload={(file) => handleFileSelected(file, activeChatId)}
          />
        </div>
      </aside>
    </>
  );
}

function UploadCard({ uploading, label, onUpload }) {
  return (
    <label
      className={`
        flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed
        border-neutral-300 bg-white px-3 py-4 text-center transition
        hover:border-neutral-400 hover:bg-neutral-50
        ${uploading ? "pointer-events-none opacity-60" : ""}
      `}
    >
      <input
        type="file"
        accept="application/pdf"
        className="hidden"
        disabled={uploading}
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) onUpload(f);
          e.target.value = "";
        }}
      />
      <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-neutral-900 text-white">
        <FileIcon className="h-3.5 w-3.5" />
      </div>
      <p className="mt-1.5 text-xs font-semibold text-neutral-800">
        {uploading ? "Indexing PDF..." : label}
      </p>
      <p className="mt-0.5 text-[10px] text-neutral-400">
        Chunks & vector embeddings
      </p>
    </label>
  );
}