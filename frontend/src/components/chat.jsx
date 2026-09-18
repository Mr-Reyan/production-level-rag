"use client";

import { useState } from "react";
import { SendIcon, FileIcon } from "./icons";

export function EmptyState({ ready, onSelectSuggestion }) {
  const suggestions = [
    "Summarize this document in 3 bullets.",
    "What are the key takeaways?",
    "List any dates or deadlines mentioned.",
  ];

  return (
    <div className="mx-auto flex max-w-2xl flex-col items-center px-4 py-16 text-center sm:py-24">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-neutral-900 text-white shadow-sm">
        <SparkIconLarge />
      </div>
      <h2 className="mt-5 text-xl font-semibold tracking-tight">
        {ready ? "Ask anything about your document" : "Upload a PDF to begin"}
      </h2>
      <p className="mt-2 max-w-md text-sm leading-relaxed text-neutral-500">
        {ready
          ? "Answers are grounded in the content of your PDF. Sources are cited below each response."
          : "Once uploaded, we chunk, embed, and index it so you can ask questions directly."}
      </p>

      {ready && (
        <div className="mt-8 grid w-full gap-2 sm:grid-cols-3">
          {suggestions.map((s) => (
            <SuggestionChip
              key={s}
              label={s}
              onSelect={() => onSelectSuggestion?.(s)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function SuggestionChip({ label, onSelect }) {
  return (
    <button
      type="button"
      className="rounded-xl border border-neutral-200 bg-white px-3 py-2.5 text-left text-xs text-neutral-700 transition hover:border-neutral-300 hover:bg-neutral-50"
      onClick={onSelect}
    >
      {label}
    </button>
  );
}

function SparkIconLarge() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"
      strokeLinecap="round" strokeLinejoin="round" className="h-6 w-6">
      <path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

export function UserBubble({ text }) {
  return (
    <div className="animate-fade-up flex justify-end">
      <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-neutral-900 px-4 py-2.5 text-sm leading-relaxed text-white sm:max-w-[75%]">
        {text}
      </div>
    </div>
  );
}

export function AssistantBubble({
  text,
  sources,
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="animate-fade-up flex gap-3">
      <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white ring-1 ring-neutral-200">
        <SparkIconSmall />
      </div>

      <div className="min-w-0 flex-1">
        <div className="whitespace-pre-wrap text-sm leading-relaxed text-neutral-900">
          {text}
        </div>

        {sources.length > 0 && (
          <div className="mt-3">
            <button
              onClick={() => setOpen((v) => !v)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-neutral-200 bg-white px-2.5 py-1 text-xs font-medium text-neutral-600 hover:bg-neutral-50"
            >
              <FileIcon className="h-3.5 w-3.5" />
              {open ? "Hide" : "Show"} {sources.length} source
              {sources.length === 1 ? "" : "s"}
            </button>

            {open && (
              <ul className="mt-3 space-y-2">
                {sources.map((s) => (
                  <li
                    key={s.id}
                    className="rounded-xl border border-neutral-200 bg-white p-3"
                  >
                    <div className="mb-1.5 flex items-center justify-between text-[11px] text-neutral-500">
                      <span className="rounded-md bg-neutral-100 px-1.5 py-0.5 font-mono">
                        {((Number(s.similarity) || 0) * 100).toFixed(1)}% match
                      </span>
                      <span className="font-mono">
                        #{s.source_id ? String(s.source_id).slice(0, 6) : "source"}
                      </span>
                    </div>
                    <p className="line-clamp-5 whitespace-pre-wrap text-xs leading-relaxed text-neutral-700">
                      {s.content}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export function ThinkingBubble() {
  return (
    <div className="animate-fade-up flex gap-3">
      <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white ring-1 ring-neutral-200">
        <SparkIconSmall />
      </div>
      <div className="flex items-center gap-1 pt-2.5">
        <Dot delay="0ms" />
        <Dot delay="150ms" />
        <Dot delay="300ms" />
      </div>
    </div>
  );
}

function Dot({ delay }) {
  return (
    <span
      className="h-1.5 w-1.5 animate-bounce rounded-full bg-neutral-400"
      style={{ animationDelay: delay }}
    />
  );
}

function SparkIconSmall() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75"
      strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4 text-neutral-700">
      <path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

export function Composer({
  value,
  onChange,
  onSubmit,
  disabled,
  pending,
  placeholder,
}) {
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
      className="border-t border-neutral-200 bg-white/80 backdrop-blur"
    >
      <div className="mx-auto flex max-w-3xl items-end gap-2 px-3 py-3 sm:px-6 sm:py-4">
        <div className="relative flex-1">
          <textarea
            data-composer
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                onSubmit();
              }
            }}
            rows={1}
            placeholder={placeholder}
            disabled={disabled || pending}
            className="
              max-h-40 w-full resize-none rounded-2xl border border-neutral-200 bg-white
              px-4 py-3 pr-12 text-sm leading-relaxed outline-none
              placeholder:text-neutral-400
              focus:border-neutral-900 focus:ring-1 focus:ring-neutral-900
              disabled:cursor-not-allowed disabled:bg-neutral-100
            "
          />
        </div>
        <button
          type="submit"
          disabled={disabled || pending || !value.trim()}
          className="
            flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl
            bg-neutral-900 text-white transition
            hover:bg-neutral-800
            disabled:cursor-not-allowed disabled:opacity-40
          "
          aria-label="Send"
        >
          <SendIcon className="h-4 w-4" />
        </button>
      </div>
      <p className="mx-auto max-w-3xl px-3 pb-2 text-center text-[11px] text-neutral-400 sm:px-6">
        Enter to send · Shift + Enter for newline
      </p>
    </form>
  );
}