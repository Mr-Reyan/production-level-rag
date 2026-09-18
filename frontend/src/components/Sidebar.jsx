"use client";

import { FileIcon, XIcon, SparkIcon } from "./icons";



export function Sidebar({
  pdfName,
  chunkCount,
  uploading,
  onUpload,
  onReset,
  mobileOpen,
  onMobileClose,
}) {
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
          fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r border-neutral-200 bg-white
          transition-transform md:static md:translate-x-0
          ${mobileOpen ? "translate-x-0" : "-translate-x-full"}
        `}
      >
        {/* Brand */}
        <div className="flex items-center justify-between px-5 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-neutral-900 text-white">
              <SparkIcon className="h-4 w-4" />
            </div>
            <div className="leading-tight">
              <div className="text-sm font-semibold">Doc Q&A</div>
              <div className="text-xs text-neutral-500">RAG over PDFs</div>
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

        {/* Document card */}
        <div className="px-4">
          <div className="text-[11px] font-medium uppercase tracking-wider text-neutral-500">
            Document
          </div>

          {pdfName ? (
            <div className="mt-2 rounded-xl border border-neutral-200 bg-neutral-50 p-3">
              <div className="flex items-start gap-2.5">
                <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-white ring-1 ring-neutral-200">
                  <FileIcon className="h-4 w-4 text-neutral-600" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-neutral-900">
                    {pdfName}
                  </p>
                  <p className="mt-0.5 text-xs text-neutral-500">
                    {chunkCount} chunk{chunkCount === 1 ? "" : "s"} indexed
                  </p>
                </div>
              </div>

              <button
                onClick={onReset}
                className="mt-3 w-full rounded-lg border border-neutral-200 bg-white px-3 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-50"
              >
                Upload another
              </button>
            </div>
          ) : (
            <UploadCard uploading={uploading} onUpload={onUpload} />
          )}
        </div>

        {/* Tips */}
        <div className="mt-auto px-4 pb-5">
          <div className="rounded-xl border border-dashed border-neutral-200 p-3">
            <p className="text-xs font-medium text-neutral-700">Tips</p>
            <ul className="mt-1.5 space-y-1 text-xs text-neutral-500">
              <li>· Ask in natural language</li>
              <li>· Cite-aware answers</li>
              <li>· Works on scanned PDFs? No — text only</li>
            </ul>
          </div>
        </div>
      </aside>
    </>
  );
}

function UploadCard({uploading, onUpload}){
  return (
    <label
      className={`
        mt-2 flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed
        border-neutral-200 px-4 py-6 text-center transition
        hover:border-neutral-300 hover:bg-neutral-50
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
        }}
      />
      <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-neutral-900 text-white">
        <FileIcon className="h-4 w-4" />
      </div>
      <p className="mt-2 text-sm font-medium text-neutral-800">
        {uploading ? "Indexing…" : "Upload PDF"}
      </p>
      <p className="mt-0.5 text-xs text-neutral-500">
        We'll chunk, embed, and index it.
      </p>
    </label>
  );
}