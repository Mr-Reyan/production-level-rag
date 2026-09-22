const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

export async function uploadPdf(file, chatId = null) {
  const form = new FormData();
  form.append("file", file);
  if (chatId) {
    form.append("chat_id", chatId);
  }

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

export async function askQuestion(chatId, question) {
  const res = await fetch(`${API_URL}/ask/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: chatId, question }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    const message = errorData?.error || errorData?.detail || `Ask failed: ${res.statusText}`;
    throw new Error(message);
  }
  return res.json();
}

export async function fetchChats() {
  const res = await fetch(`${API_URL}/chats/`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.error || "Failed to fetch chats");
  }
  return res.json();
}

export async function fetchChatDetail(chatId) {
  const res = await fetch(`${API_URL}/chats/${chatId}/`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.error || "Failed to fetch chat details");
  }
  return res.json();
}

export async function deleteChat(chatId) {
  const res = await fetch(`${API_URL}/chats/${chatId}/`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.error || "Failed to delete chat");
  }
  return res.json();
}