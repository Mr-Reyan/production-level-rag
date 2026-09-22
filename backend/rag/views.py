import json
import logging
import uuid
import requests
from django.conf import settings
from django.db import connection, transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view

from rag.models import Chats, Message, Document
from rag.services import embed, derive_chat_title, ingest_pdf, extract_tables_and_text

logger = logging.getLogger(__name__)


@csrf_exempt
@api_view(["GET"])
def list_chats(request):
    """
    List all active chats ordered by latest creation.
    """
    try:
        chats = Chats.objects.filter(deleted_at__isnull=True).order_by("-created_at")
        data = [
            {
                "id": str(chat.id),
                "title": chat.title,
                "created_at": chat.created_at.isoformat() if chat.created_at else None,
                "message_count": chat.messages.count(),
            }
            for chat in chats
        ]
        return JsonResponse({"chats": data}, status=200)
    except Exception as e:
        logger.error(f"Error listing chats: {e}", exc_info=True)
        return JsonResponse({"error": f"Failed to list chats: {str(e)}"}, status=500)


@csrf_exempt
@api_view(["GET", "DELETE"])
def chat_detail(request, chat_id):
    """
    GET: Retrieve chat info, message history, and associated documents.
    DELETE: Soft-delete a chat.
    """
    chat = Chats.objects.filter(id=chat_id, deleted_at__isnull=True).first()
    if not chat:
        return JsonResponse({"error": "Chat not found"}, status=404)

    if request.method == "DELETE":
        try:
            chat.deleted_at = timezone.now()
            chat.save(update_fields=["deleted_at"])
            return JsonResponse({"message": "Chat deleted successfully", "chat_id": str(chat.id)}, status=200)
        except Exception as e:
            return JsonResponse({"error": f"Failed to delete chat: {str(e)}"}, status=500)

    # GET: return chat details, messages, and uploaded document titles
    try:
        messages = [
            {
                "id": m.id,
                "sender": m.sender,
                "text": m.text,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in chat.messages.all().order_by("created_at")
        ]
        docs = list(
            chat.documents.values("source_id", "title")
            .distinct()
        )
        return JsonResponse(
            {
                "chat": {
                    "id": str(chat.id),
                    "title": chat.title,
                    "created_at": chat.created_at.isoformat() if chat.created_at else None,
                },
                "messages": messages,
                "documents": [{"source_id": str(d["source_id"]), "title": d["title"]} for d in docs],
            },
            status=200,
        )
    except Exception as e:
        logger.error(f"Error fetching chat detail: {e}", exc_info=True)
        return JsonResponse({"error": f"Failed to fetch chat details: {str(e)}"}, status=500)


@csrf_exempt
@api_view(["POST"])
def upload_pdf(request):
    """
    Upload a PDF document.
    - If `chat_id` is provided in POST body or query params, attaches the PDF chunks to that chat.
    - If `chat_id` is omitted, automatically creates a new Chat with a new UUID and derived title.
    """
    if "file" not in request.FILES:
        return JsonResponse({"error": "No file provided under 'file' form-data key"}, status=400)

    pdf_file = request.FILES["file"]
    if not pdf_file.name.lower().endswith(".pdf"):
        return JsonResponse({"error": "Only PDF files are supported"}, status=400)

    # Check if a chat_id was provided
    chat_id = request.POST.get("chat_id") or request.GET.get("chat_id") or request.data.get("chat_id")
    chat = None

    if chat_id:
        chat = Chats.objects.filter(id=chat_id, deleted_at__isnull=True).first()
        if not chat:
            return JsonResponse({"error": f"Chat with ID '{chat_id}' does not exist"}, status=404)

    # Derive chat title if this is a new chat
    chat_title = None
    if not chat:
        try:
            chat_title = derive_chat_title(pdf_file, fallback_title=pdf_file.name.replace(".pdf", ""))
        except Exception:
            chat_title = pdf_file.name.replace(".pdf", "")

    source_id = uuid.uuid4()

    try:
        with transaction.atomic():
            if not chat:
                chat = Chats.objects.create(title=chat_title or "New Chat")

            chunks = ingest_pdf(pdf_file, chat=chat, title=pdf_file.name, source_id=source_id)

        if not chunks:
            return JsonResponse(
                {"error": "Could not extract readable text or tables from this PDF."},
                status=400,
            )

        return JsonResponse(
            {
                "chat_id": str(chat.id),
                "chat_title": chat.title,
                "source_id": str(source_id),
                "title": pdf_file.name,
                "chunks_count": len(chunks),
            },
            status=201,
        )
    except Exception as e:
        logger.error(f"PDF upload processing failed: {e}", exc_info=True)
        return JsonResponse({"error": f"Failed to process and store PDF: {str(e)}"}, status=500)


@csrf_exempt
@api_view(["POST"])
def ask(request):
    """
    RAG Question Answering strictly isolated to the specified `chat_id`.
    - Stores the user's question in Message table.
    - Performs vector similarity search strictly on Document rows belonging to `chat_id`.
    - Generates an answer from context via Ollama.
    - Stores the AI answer in Message table.
    """
    try:
        body = json.loads(request.body) if request.body else request.data
    except Exception:
        body = request.data or {}

    question = str(body.get("question", "")).strip()
    chat_id = body.get("chat_id")

    if not chat_id:
        return JsonResponse({"error": "'chat_id' is required to ask a question"}, status=400)

    if not question:
        return JsonResponse({"error": "'question' cannot be empty"}, status=400)

    chat = Chats.objects.filter(id=chat_id, deleted_at__isnull=True).first()
    if not chat:
        return JsonResponse({"error": f"Chat with ID '{chat_id}' does not exist"}, status=404)

    # 1. Record the user message
    try:
        Message.objects.create(chat=chat, text=question, sender="user")
    except Exception as e:
        logger.warning(f"Could not save user message: {e}")

    # 2. Embed the question
    try:
        query_vector = embed(question)
    except Exception as e:
        return JsonResponse({"error": f"Failed to generate embedding for query: {str(e)}"}, status=500)

    # 3. Chat-isolated pgvector similarity search
    # Strictly filters `WHERE chat_id = %s` so no cross-chat context can ever leak
    chunks = []
    try:
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT id, content, source_id, title, (1 - (embedding <=> %s::vector)) AS similarity
                FROM rag_document
                WHERE chat_id = %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                [query_vector, str(chat.id), query_vector, 5],
            )
            rows = cur.fetchall()

        chunks = [
            {
                "id": r[0],
                "content": r[1],
                "source_id": str(r[2]),
                "title": r[3],
                "similarity": round(float(r[4]), 4),
            }
            for r in rows
        ]
    except Exception as e:
        logger.error(f"Vector search failed: {e}", exc_info=True)
        return JsonResponse({"error": f"Vector similarity search failed: {str(e)}"}, status=500)

    # If no documents are attached to this chat
    if not chunks:
        fallback_answer = "I don't have any documents uploaded in this chat to answer your question. Please upload a PDF to this chat first."
        Message.objects.create(chat=chat, text=fallback_answer, sender="ai")
        return JsonResponse(
            {
                "chat_id": str(chat.id),
                "answer": fallback_answer,
                "sources": [],
            },
            status=200,
        )

    # 4. Construct context and prompt
    context_text = "\n\n---\n\n".join(
        f"[From '{c['title']}']:\n{c['content']}" for c in chunks
    )
    prompt = f"""You are a helpful and precise assistant. Answer the question using ONLY the provided document context below.
If the answer cannot be found in the provided context, answer with: "I don't know based on the provided documents in this chat."
Do not guess, hallucinate, or use outside unverified facts.

Context:
{context_text}

Question: {question}
Answer:"""

    ollama_url = getattr(settings, "OLLAMA_URL", "http://localhost:11434")
    model = getattr(settings, "OLLAMA_LLM_MODEL", "gemma4:31b-cloud")

    try:
        res = requests.post(
            f"{ollama_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=120,
        )
        if res.status_code != 200:
            err_msg = res.text
            try:
                err_msg = res.json().get("error", res.text)
            except Exception:
                pass
            return JsonResponse(
                {"error": f"Ollama generation failed ({res.status_code}): {err_msg}"},
                status=502,
            )

        llm_response = res.json()
        answer = llm_response.get("response", "").strip()
        if not answer:
            answer = "Unable to generate a response from LLM."

        # 5. Record the AI response
        Message.objects.create(chat=chat, text=answer, sender="ai")

        return JsonResponse(
            {
                "chat_id": str(chat.id),
                "answer": answer,
                "sources": chunks,
            },
            status=200,
        )

    except requests.exceptions.ConnectionError:
        return JsonResponse(
            {
                "error": f"Could not connect to Ollama at {ollama_url}. Please ensure Ollama is running (`ollama serve`)."
            },
            status=502,
        )
    except requests.exceptions.Timeout:
        return JsonResponse(
            {"error": "LLM generation timed out after 120 seconds."},
            status=504,
        )
    except Exception as e:
        logger.error(f"LLM generation failed: {e}", exc_info=True)
        return JsonResponse({"error": f"Generation error: {str(e)}"}, status=500)

