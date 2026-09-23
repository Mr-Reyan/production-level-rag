import logging
import requests
import tiktoken
from django.conf import settings
from chats.models import Message

logger = logging.getLogger(__name__)

try:
    _encoding = tiktoken.get_encoding("cl100k_base")
except Exception:
    _encoding = None


def count_tokens(text: str) -> int:
    """
    Count tokens using tiktoken (fallback to rough word count approximation).
    """
    if not text:
        return 0
    if _encoding is not None:
        try:
            return len(_encoding.encode(text))
        except Exception:
            pass
    return max(1, len(text.split()))


def get_recent_messages(chat, user_limit: int = 5, ai_limit: int = 5) -> list[Message]:
    """
    Retrieves the latest 10 messages (up to 5 from user and 5 from AI),
    ordered chronologically for LLM context.
    """
    user_msgs = list(
        Message.objects.filter(chat=chat, sender="user").order_by("-created_at")[:user_limit]
    )
    ai_msgs = list(
        Message.objects.filter(chat=chat, sender="ai").order_by("-created_at")[:ai_limit]
    )
    combined = sorted(user_msgs + ai_msgs, key=lambda m: m.created_at)
    return combined


def get_total_chat_tokens(chat) -> int:
    """
    Calculate the total token count of all messages in a chat.
    """
    msgs = Message.objects.filter(chat=chat).values_list("text", flat=True)
    return sum(count_tokens(text) for text in msgs)


def get_history_within_budget(chat, max_tokens: int = 2000) -> str:
    """
    Builds a conversation history string from the most recent messages up to max_tokens budget.
    """
    msgs = Message.objects.filter(chat=chat).order_by("-created_at")
    picked, total = [], 0
    for m in msgs:
        t = count_tokens(m.text)
        if total + t > max_tokens:
            break
        picked.append(m)
        total += t

    picked.reverse()
    return "\n".join(f"{'User' if m.sender == 'user' else 'Assistant'}: {m.text}" for m in picked)


def get_summary(history_text: str) -> str:
    """
    Generates a concise summary of the conversation using Ollama LLM.
    """
    if not history_text or not history_text.strip():
        return ""

    ollama_url = getattr(settings, "OLLAMA_URL", "http://localhost:11434")
    model = getattr(settings, "OLLAMA_LLM_MODEL", "gemma4:31b-cloud")

    prompt = f"""You are an expert summarizer. Summarize the following conversation concisely into 2-4 sentences, highlighting key questions asked and topics discussed.

Conversation:
{history_text}

Concise Summary:"""

    try:
        res = requests.post(
            f"{ollama_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=30,
        )
        if res.status_code == 200:
            answer = res.json().get("response", "").strip()
            if answer:
                return answer
    except Exception as e:
        logger.warning(f"Ollama chat summarization failed: {e}")

    return ""


import threading

def summarize_chat(chat) -> str:
    """
    Summarizes all messages in the chat and updates chat.summary.
    """
    msgs = Message.objects.filter(chat=chat).order_by("created_at")
    if not msgs.exists():
        return ""

    history = "\n".join(
        f"{'User' if m.sender == 'user' else 'Assistant'}: {m.text}" for m in msgs
    )
    summary = get_summary(history)
    if summary:
        chat.summary = summary
        chat.save(update_fields=["summary"])
    return summary


def auto_summarize_if_exceeds_budget(chat, token_threshold: int = 2000) -> bool:
    """
    Checks if total tokens in chat exceed token_threshold (2000).
    Runs summarization in a background thread so it never delays user queries.
    """
    total_tokens = get_total_chat_tokens(chat)
    if total_tokens >= token_threshold:
        logger.info(
            f"Chat {chat.id} has {total_tokens} tokens (>= {token_threshold}). Launching background summary..."
        )
        t = threading.Thread(target=summarize_chat, args=(chat,), daemon=True)
        t.start()
        return True
    return False


def should_retrieve(query: str, recent_history_text: str = "", summary: str = "") -> bool:
    """
    Fast intent check using llama3.2:3b to determine if the query requires retrieving new chunks
    from the pgvector document database, or if it is a conversational remark/follow-up.
    """
    clean_q = query.strip().lower()

    # Fast heuristics for trivial conversational queries
    trivial_phrases = {
        "hi", "hello", "hey", "thanks", "thank you", "bye", "goodbye",
        "ok", "okay", "cool", "great", "who are you", "what can you do",
    }
    if clean_q in trivial_phrases or clean_q.rstrip("!?.") in trivial_phrases:
        return False

    ollama_url = getattr(settings, "OLLAMA_URL", "http://localhost:11434")
    model = getattr(settings, "OLLAMA_ROUTER_MODEL", "llama3.2:3b")

    prompt = f"""You are a query router for a Document Q&A system.
Determine if answering requires searching and retrieving factual information from an uploaded document (YES), or if it can be answered purely using general conversational knowledge or recent chat context (NO) (e.g. "what was the 2nd one?", "explain more", "summarize what we discussed", greetings).

Recent Chat:
{recent_history_text[-400:] if recent_history_text else "No prior history"}

User Query: "{query}"

Respond with ONLY the word "YES" or "NO".
Decision:"""

    try:
        res = requests.post(
            f"{ollama_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.0, "num_predict": 5},
            },
            timeout=5,
        )
        if res.status_code == 200:
            decision = res.json().get("response", "").strip().upper()
            if "NO" in decision and "YES" not in decision:
                return False
            if "YES" in decision:
                return True
    except Exception as e:
        logger.info(f"Intent router fallback ({e}), defaulting to retrieval.")

    # Safe default: perform retrieval so no document context is missed
    return True
