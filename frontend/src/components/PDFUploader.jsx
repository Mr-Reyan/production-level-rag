"use client";
import { useState } from "react";

export function PdfUploader({ onUploaded }) {
  const [uploading, setUploading] = useState(false);

  async function handleUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    setUploading(true);

    const form = new FormData();
    form.append("file", file);

    const res = await fetch("http://localhost:8000/api/upload/", {
      method: "POST",
      body: form,
    });
    const data = await res.json();
    setUploading(false);
    onUploaded?.(data);
  }

  return (
    <div>
      <input type="file" accept="application/pdf" onChange={handleUpload} />
      {uploading && <p>Uploading and indexing…</p>}
    </div>
  );
}