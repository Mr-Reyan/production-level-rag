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
  let answer = "";
  let sources = [];
  await askQuestionStream(chatId, question, {
    onToken: (t) => {
      answer += t;
    },
    onSources: (s) => {
      sources = s;
    },
  });
  return { answer, sources };
}

export async function askQuestionStream(chatId, question, { onToken, onSources, onDone, onError } = {}) {
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

  const reader = res.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n\n");
    buffer = lines.pop(); // preserve unfinished chunk

    for (const chunk of lines) {
      const line = chunk.trim();
      if (!line || !line.startsWith("data:")) continue;
      const jsonStr = line.replace(/^data:\s*/, "");
      try {
        const data = JSON.parse(jsonStr);
        if (data.type === "sources") {
          onSources?.(data.sources || []);
        } else if (data.type === "token") {
          onToken?.(data.token);
        } else if (data.type === "done") {
          onDone?.(data);
        } else if (data.type === "error") {
          onError?.(new Error(data.error));
        }
      } catch (e) {
        console.error("Error parsing stream chunk:", e);
      }
    }
  }
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