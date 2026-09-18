// "use client";

// import { useRef, useState, useEffect } from "react";
// import { useUploadPdf, useAsk } from "@/hooks/use-rag";

// export default function Home() {
//   const [messages, setMessages] = useState([]);
//   const [input, setInput] = useState("");
//   const [pdfName, setPdfName] = useState(null);
//   const fileRef = useRef(null);
//   const scrollRef = useRef(null);

//   const upload = useUploadPdf();
//   const ask = useAsk();


//   useEffect(() => {
//     scrollRef.current?.scrollTo({
//       top: scrollRef.current.scrollHeight,
//       behavior: "smooth",
//     });
//   }, [messages, ask.isPending]);

//   async function handleFile(e) {
//     const file = e.target.files?.[0];
//     if (!file) return;

//     setPdfName(file.name);
//     upload.mutate(file, {
//       onSuccess: () => {
//         setMessages([]);
//         if (fileRef.current) fileRef.current.value = "";
//       },
//     });
//   }

//   async function handleSend(e) {
//     e.preventDefault();
//     const q = input.trim();
//     if (!q || ask.isPending) return;

//     setMessages((m) => [...m, { role: "user", content: q }]);
//     setInput("");

//     ask.mutate(q, {
//       onSuccess: (data) => {
//         setMessages((m) => [
//           ...m,
//           { role: "assistant", content: data.answer, sources: data.sources },
//         ]);
//       },
//       onError: (err) => {
//         setMessages((m) => [
//           ...m,
//           {
//             role: "assistant",
//             content: `Error: ${err.message}`,
//             sources: [],
//           },
//         ]);
//       },
//     });
//   }

//   const ready = !!pdfName && upload.isSuccess;
//   const indexed = upload.data?.chunks ?? 0;

//   return (
//     <main className="flex h-dvh flex-col bg-neutral-50">
//       {/* Header */}
//       <header className="border-b border-neutral-200 bg-white">
//         <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-3 sm:px-6">
//           <div className="flex items-center gap-3">
//             <div className="h-8 w-8 rounded-lg bg-neutral-900" />
//             <div>
//               <h1 className="text-sm font-semibold leading-tight">Doc Q&A</h1>
//               <p className="text-xs text-neutral-500 leading-tight">
//                 {pdfName
//                   ? `${pdfName} · ${indexed} chunks`
//                   : "Upload a PDF to begin"}
//               </p>
//             </div>
//           </div>

//           <label className="cursor-pointer rounded-lg border border-neutral-300 bg-white px-3 py-1.5 text-xs font-medium hover:bg-neutral-100">
//             <input
//               ref={fileRef}
//               type="file"
//               accept="application/pdf"
//               onChange={handleFile}
//               className="hidden"
//               disabled={upload.isPending}
//             />
//             {upload.isPending
//               ? "Indexing…"
//               : ready
//               ? "Replace PDF"
//               : "Upload PDF"}
//           </label>
//         </div>

//         {upload.isError && (
//           <div className="mx-auto max-w-3xl px-4 pb-3 sm:px-6">
//             <p className="text-xs text-red-600">
//               Failed to upload: {upload.error.message}
//             </p>
//           </div>
//         )}
//       </header>

//       {/* Chat area */}
//       <div ref={scrollRef} className="flex-1 overflow-y-auto">
//         <div className="mx-auto max-w-3xl px-4 py-6 sm:px-6">
//           {messages.length === 0 && !upload.isPending && (
//             <EmptyState ready={ready} />
//           )}

//           <div className="space-y-6">
//             {messages.map((m, i) =>
//               m.role === "user" ? (
//                 <UserBubble key={i} text={m.content} />
//               ) : (
//                 <AssistantBubble
//                   key={i}
//                   text={m.content}
//                   sources={m.sources}
//                 />
//               )
//             )}

//             {ask.isPending && <ThinkingBubble />}
//           </div>
//         </div>
//       </div>

//       {/* Composer */}
//       <form
//         onSubmit={handleSend}
//         className="border-t border-neutral-200 bg-white"
//       >
//         <div className="mx-auto flex max-w-3xl items-end gap-2 px-4 py-3 sm:px-6">
//           <textarea
//             value={input}
//             onChange={(e) => setInput(e.target.value)}
//             onKeyDown={(e) => {
//               if (e.key === "Enter" && !e.shiftKey) {
//                 e.preventDefault();
//                 handleSend(e);
//               }
//             }}
//             rows={1}
//             placeholder={
//               ready ? "Ask something about the PDF…" : "Upload a PDF first"
//             }
//             disabled={!ready || ask.isPending}
//             className="max-h-40 flex-1 resize-none rounded-xl border border-neutral-300 bg-white px-3 py-2 text-sm outline-none placeholder:text-neutral-400 focus:border-neutral-900 disabled:cursor-not-allowed disabled:bg-neutral-100"
//           />
//           <button
//             type="submit"
//             disabled={!ready || ask.isPending || !input.trim()}
//             className="rounded-xl bg-neutral-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-40"
//           >
//             Send
//           </button>
//         </div>
//       </form>
//     </main>
//   );
// }

// /* ---------- Subcomponents ---------- */

// function EmptyState({ ready }) {
//   return (
//     <div className="flex flex-col items-center justify-center py-24 text-center">
//       <div className="mb-4 h-12 w-12 rounded-2xl bg-neutral-900" />
//       <h2 className="text-lg font-semibold">
//         {ready ? "Ready when you are." : "Upload a PDF to get started."}
//       </h2>
//       <p className="mt-1 max-w-sm text-sm text-neutral-500">
//         {ready
//           ? "Ask a question and the assistant will answer using only the content of your document."
//           : "Once uploaded, we'll chunk, embed, and index it so you can ask questions directly."}
//       </p>
//     </div>
//   );
// }

// function UserBubble({ text }) {
//   return (
//     <div className="flex justify-end">
//       <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-neutral-900 px-4 py-2.5 text-sm text-white">
//         {text}
//       </div>
//     </div>
//   );
// }

// function AssistantBubble({
//   text,
//   sources,
// }) {
//   const [open, setOpen] = useState(false);

//   return (
//     <div className="flex flex-col items-start gap-2">
//       <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-bl-md border border-neutral-200 bg-white px-4 py-2.5 text-sm">
//         {text}
//       </div>

//       {sources.length > 0 && (
//         <div className="w-full max-w-[85%]">
//           <button
//             onClick={() => setOpen((v) => !v)}
//             className="text-xs font-medium text-neutral-500 hover:text-neutral-900"
//           >
//             {open ? "Hide" : "Show"} {sources.length} source
//             {sources.length === 1 ? "" : "s"}
//           </button>

//           {open && (
//             <ul className="mt-2 space-y-2">
//               {sources.map((s) => (
//                 <li
//                   key={s.id}
//                   className="rounded-xl border border-neutral-200 bg-white p-3 text-xs"
//                 >
//                   <div className="mb-1 flex items-center justify-between text-neutral-500">
//                     <span>similarity {s.similarity.toFixed(3)}</span>
//                     <span className="font-mono">
//                       {s.source_id.slice(0, 8)}
//                     </span>
//                   </div>
//                   <p className="line-clamp-4 whitespace-pre-wrap text-neutral-700">
//                     {s.content}
//                   </p>
//                 </li>
//               ))}
//             </ul>
//           )}
//         </div>
//       )}
//     </div>
//   );
// }

// function ThinkingBubble() {
//   return (
//     <div className="flex items-start">
//       <div className="flex items-center gap-1 rounded-2xl rounded-bl-md border border-neutral-200 bg-white px-4 py-3">
//         <Dot delay="0ms" />
//         <Dot delay="150ms" />
//         <Dot delay="300ms" />
//       </div>
//     </div>
//   );
// }

// function Dot({ delay }) {
//   return (
//     <span
//       className="h-1.5 w-1.5 animate-bounce rounded-full bg-neutral-400"
//       style={{ animationDelay: delay }}
//     />
//   );
// }



"use client";

import { useEffect, useRef, useState } from "react";
import { useUploadPdf, useAsk } from "../hooks/use-rag";
import { Sidebar } from "../components/Sidebar";
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
          { role: "assistant", content: data.answer, sources: data.sources },
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
                : ready
                ? `${indexed} chunks indexed`
                : "Upload a PDF to start"}
            </div>
          </div>
        </header>

        {/* Messages */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto bg-neutral-50">
          {messages.length === 0 && !upload.isPending ? (
            <EmptyState ready={ready} />
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