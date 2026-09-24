import json
import logging
import time
import uuid
import requests
from django.conf import settings
from django.db import connection, transaction
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view

from chats.models import Chats, Message
from chats.services import (
    get_recent_messages,
    should_retrieve,
    auto_summarize_if_exceeds_budget,
)
from rag.services import derive_chat_title, embed, ingest_pdf, rerank
from observability.langfuse_client import langfuse

logger = logging.getLogger(__name__)


@csrf_exempt
@api_view(["POST"])
def upload_pdf(request):
    """
    Upload a PDF document.
    - If `chat_id` is provided, attaches the PDF chunks to that chat.
    - If `chat_id` is omitted, automatically creates a new Chat with a new UUID and derived title.
    """
    if "file" not in request.FILES:
        return JsonResponse({"error": "No file provided under 'file' form-data key"}, status=400)

    pdf_file = request.FILES["file"]
    if not pdf_file.name.lower().endswith(".pdf"):
        return JsonResponse({"error": "Only PDF files are supported"}, status=400)

    chat_id = request.POST.get("chat_id") or request.GET.get("chat_id") or request.data.get("chat_id")
    chat = None

    if chat_id:
        chat = Chats.objects.filter(id=chat_id, deleted_at__isnull=True).first()
        if not chat:
            return JsonResponse({"error": f"Chat with ID '{chat_id}' does not exist"}, status=404)

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
    - Streams tokens in real-time to the frontend (SSE stream).
    - Prints detailed latency breakdowns to the terminal.
    - Intent router runs on fast llama3.2:3b.
    - Retrieval fetches top 10 from pgvector and reranks to top 5 with Jina.
    """
    t_start = time.time()
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

    print("\n" + "=" * 60)
    print(f"📥 [REQUEST RECEIVED] Chat: {chat_id} | Query: '{question}'")

    # 1. Fetch prior recent 10 messages (up to 5 user + 5 AI) before adding current question
    recent_msgs = get_recent_messages(chat, user_limit=5, ai_limit=5)
    recent_history_text = "\n".join(
        f"{'User' if m.sender == 'user' else 'Assistant'}: {m.text}" for m in recent_msgs
    )

    # 2. Record the user message
    try:
        Message.objects.create(chat=chat, text=question, sender="user")
    except Exception as e:
        logger.warning(f"Could not save user message: {e}")

    ollama_url = getattr(settings, "OLLAMA_URL", "http://localhost:11434")
    model = getattr(settings, "OLLAMA_LLM_MODEL", "gemma4:31b-cloud")

    trace = langfuse.start_observation(
        name="rag-ask",
        as_type="span",
        input={"question": question, "chat_id": str(chat.id)},
        metadata={"model": model, "chat_id": str(chat.id)},
    )
    trace_id = trace.trace_id
    print(f"Trace ID: {trace_id}")
    retrieval_span = trace.start_observation(name="retrieval", as_type="retriever", input={"query": question})

    # 3. Check token budget (background auto-summarization only if >= 2000 tokens)
    auto_summarize_if_exceeds_budget(chat, token_threshold=2000)

    # 4. Intent router
    t_router = time.time()
    needs_retrieval = should_retrieve(
        query=question,
        recent_history_text=recent_history_text,
        summary=chat.summary,
    )
    router_time = time.time() - t_router
    print(f"⏱️ [Intent Router] Decision: {'RETRIEVE' if needs_retrieval else 'SKIP'} ({router_time:.2f}s)")

    chunks = []
    raw_chunks = []
    ret_time = 0.0
    reranked_flag = False
    if needs_retrieval:
        t_ret = time.time()
        try:
            # Embed question
            query_vector = embed(question)

            # Chat-isolated pgvector similarity search (fetch top 10)
            with connection.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, content, source_id, title, (1 - (embedding <=> %s::vector)) AS similarity
                    FROM rag_document
                    WHERE chat_id = %s
                    ORDER BY embedding <=> %s::vector
                    LIMIT 6
                    """,
                    [query_vector, str(chat.id), query_vector],
                )
                rows = cur.fetchall()

            raw_chunks = [
                {
                    "id": r[0],
                    "content": r[1],
                    "source_id": str(r[2]),
                    "title": r[3],
                    "similarity": round(float(r[4]), 4),
                }
                for r in rows
            ]

            # Rerank top 10 candidates to top 5 using Jina Reranker
            if raw_chunks:
                chunks, reranked_flag = rerank(question, raw_chunks, top_k=3)
                if not reranked_flag:
                    print("⚠️ [Rerank] Using vector-only chunks (API fallback).")

            ret_time = time.time() - t_ret
            print(f"⏱️ [Retrieval & Rerank] Retrieved {len(raw_chunks)} chunks, reranked top {len(chunks)} in {ret_time:.2f}s")
        except Exception as e:
            logger.error(f"Vector search or reranking failed: {e}", exc_info=True)
            chunks = []

    retrieval_span.update(
        output={"chunks": chunks},
        metadata={
            "needs_retrieval": needs_retrieval,
            "reranked": reranked_flag,
            "raw_count": len(raw_chunks) if needs_retrieval else 0,
            "final_count": len(chunks),
            "router_time_s": round(router_time, 3),
            "retrieval_time_s": round(ret_time, 3) if needs_retrieval else 0,
        },
    )
    retrieval_span.end()

    # 5. Construct comprehensive prompt
    prompt_sections = [
        "You are a helpful, highly capable, and precise AI assistant in a Document Q&A system."
    ]

    if chat.summary and chat.summary.strip():
        prompt_sections.append(f"### Previous Conversation Summary:\n{chat.summary.strip()}")

    if recent_history_text:
        prompt_sections.append(f"### Recent Conversation History:\n{recent_history_text}")

    if chunks:
        doc_context = "\n\n---\n\n".join(
            f"[From '{c['title']}']:\n{c['content']}" for c in chunks
        )
        prompt_sections.append(f"### Relevant Document Context:\n{doc_context}")
        prompt_sections.append(
            "Instructions: Answer the question accurately using the provided document context and conversation history. "
            "If the answer cannot be found in the provided context or history, say \"I don't know based on the provided documents in this chat.\" "
            "Do not guess or hallucinate."
        )
    else:
        prompt_sections.append(
            "Instructions: Answer the user's question clearly, politely, and helpfully using the conversation context above."
        )

    prompt_sections.append(f"User Question: {question}\nAnswer:")
    full_prompt = "\n\n".join(prompt_sections)

    print(f"🚀 [LLM Generation Started] Model: {model} | Elapsed so far: {time.time() - t_start:.2f}s")

    generation = trace.start_observation(
        name="llm-generation",
        as_type="generation",
        model=model,
        input=full_prompt,
        metadata={"provider": "ollama"},
    )

    # 6. Stream tokens via SSE
    def event_stream():
        # Emit initial sources metadata event
        yield f"data: {json.dumps({'type': 'sources', 'sources': chunks, 'retrieval_used': bool(chunks and needs_retrieval)})}\n\n"

        full_answer_chunks = []
        ttft_recorded = False

        try:
            res = requests.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": model,
                    "prompt": full_prompt,
                    "stream": True,
                    "keep_alive": "30m",         
                    "options": {
                        "num_ctx": 4096,         
                    },
                },
                stream=True,
                timeout=120,
            )

            if res.status_code != 200:
                err_msg = f"Ollama generation error ({res.status_code})"
                yield f"data: {json.dumps({'type': 'error', 'error': err_msg})}\n\n"
                generation.update(output=None, level="ERROR", status_message=err_msg)
                generation.end()
                trace.update(output=None, level="ERROR", status_message=err_msg)
                trace.end()
                langfuse.flush()
                return

            final_usage = {}

            for line in res.iter_lines():
                if not line:
                    continue
                try:
                    payload = json.loads(line.decode("utf-8"))
                    token = payload.get("response", "")
                    if token:
                        if not ttft_recorded:
                            ttft = time.time() - t_start
                            print(f"⚡ [TTFT - Time To First Token] {ttft:.2f}s from send click!")
                            ttft_recorded = True
                        full_answer_chunks.append(token)
                        yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"

                    if payload.get("done", False):
                        final_usage = {
                            "input": payload.get("prompt_eval_count", 0),
                            "output": payload.get("eval_count", 0),
                            "total": payload.get("prompt_eval_count", 0) + payload.get("eval_count", 0),
                        }
                        break
                except Exception as parse_err:
                    logger.warning(f"Error parsing stream chunk: {parse_err}")
                    continue

        except Exception as stream_err:
            logger.error(f"Streaming error: {stream_err}", exc_info=True)
            generation.update(output=None, level="ERROR", status_message=str(stream_err))
            generation.end()
            trace.update(output=None, level="ERROR", status_message=str(stream_err))
            trace.end()
            yield f"data: {json.dumps({'type': 'error', 'error': str(stream_err)})}\n\n"
            langfuse.flush()
            return

        total_req_time = time.time() - t_start
        print(f"✅ [Total Request Completed] Finished streaming in {total_req_time:.2f}s total.")
        print("=" * 60 + "\n")

        full_answer = "".join(full_answer_chunks).strip() or "Unable to generate a response from LLM."

        generation.update(
            output=full_answer,
            usage_details=final_usage or None,
            metadata={"total_time_s": round(total_req_time, 3)},
        )
        generation.end()

        trace.update(output=full_answer)
        trace.end()

        # Save AI message with sources
        try:
            retrieved_chunk_ids = [c["id"] for c in chunks]
            Message.objects.create(chat=chat, text=full_answer, sender="ai", sources=chunks, retrieved_chunk_ids=retrieved_chunk_ids, trace_id=trace_id)

            auto_summarize_if_exceeds_budget(chat, token_threshold=2000)
        except Exception as e:
            logger.warning(f"Could not save AI message: {e}")

        yield f"data: {json.dumps({'type': 'done', 'total_time': round(total_req_time, 2)})}\n\n"

        langfuse.flush()

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
