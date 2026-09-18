const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

export async function uploadPdf(file) {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${API_URL}/upload/`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    const message = errorData?.error || errorData?.detail || `Upload failed: ${res.statusText}`;
    throw new Error(message);
  }
  return res.json();
}

export async function askQuestion(question) {
  const res = await fetch(`${API_URL}/ask/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    const message = errorData?.error || errorData?.detail || `Ask failed: ${res.statusText}`;
    throw new Error(message);
  }
  return res.json();
}