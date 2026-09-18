import json
import uuid
import requests
from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view

from .models import Document
from .services import chunk_text, embed, extract_text_from_pdf


@csrf_exempt
@api_view(["POST"])
def add_document(request):
    try:
        body = json.loads(request.body)
    except Exception:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    title = body.get("title", "").strip()
    content = body.get("content", "").strip()
    if not title or not content:
        return JsonResponse({"error": "'title' and 'content' are required fields"}, status=400)

    try:
        query_vector = embed(content)
        doc = Document.objects.create(
            title=title,
            content=content,
            embedding=query_vector,
            source_id=uuid.uuid4(),
            chunk_index=0,
        )
        return JsonResponse({"id": doc.id, "title": doc.title}, status=201)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@api_view(["POST"])
def search(request):
    try:
        body = json.loads(request.body)
    except Exception:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    query = body.get("query", "").strip()
    if not query:
        return JsonResponse({"error": "'query' is required"}, status=400)

    top_k = body.get("top_k", 5)
    try:
        top_k = int(top_k)
    except (ValueError, TypeError):
        top_k = 5

    try:
        query_vector = embed(query)
        with connection.cursor() as cur:
            cur.execute(
                "SELECT id, content, similarity FROM match_documents(%s::vector, %s)",
                [query_vector, top_k],
            )
            rows = cur.fetchall()

        results = [{"id": r[0], "content": r[1], "similarity": float(r[2])} for r in rows]
        return JsonResponse({"results": results})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@api_view(["POST"])
def upload_pdf(request):
    if "file" not in request.FILES:
        return JsonResponse({"error": "No file provided under 'file' key"}, status=400)

    pdf_file = request.FILES["file"]
    if not pdf_file.name.lower().endswith(".pdf"):
        return JsonResponse({"error": "Only PDF files are supported"}, status=400)

    source_id = uuid.uuid4()

    try:
        text = extract_text_from_pdf(pdf_file)
    except Exception as e:
        return JsonResponse({"error": f"Failed to parse PDF: {str(e)}"}, status=400)

    if not text:
        return JsonResponse(
            {
                "error": "Could not extract readable text from this PDF. It may be scanned, image-only, or empty."
            },
            status=400,
        )

    chunks = chunk_text(text)
    if not chunks:
        return JsonResponse(
            {"error": "No text chunks could be generated from the document."},
            status=400,
        )

    try:
        created_docs = []
        for i, chunk in enumerate(chunks):
            embedding = embed(chunk)
            created_docs.append(
                Document(
                    title=pdf_file.name,
                    content=chunk,
                    embedding=embedding,
                    source_id=source_id,
                    chunk_index=i,
                )
            )
        Document.objects.bulk_create(created_docs)
        return JsonResponse(
            {
                "source_id": str(source_id),
                "title": pdf_file.name,
                "chunks": len(chunks),
            },
            status=201,
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@api_view(["POST"])
def ask(request):
    try:
        body = json.loads(request.body)
    except Exception:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    question = body.get("question", "").strip()
    if not question:
        return JsonResponse({"error": "'question' is required"}, status=400)

    try:
        query_vector = embed(question)
        with connection.cursor() as c:
            c.execute(
                "SELECT id, content, source_id, similarity FROM match_documents(%s::vector, %s)",
                [query_vector, 5],
            )
            rows = c.fetchall()

        chunks = [
            {
                "id": r[0],
                "content": r[1],
                "source_id": str(r[2]),
                "similarity": float(r[3]),
            }
            for r in rows
        ]
    except Exception as e:
        return JsonResponse({"error": f"Search failed: {str(e)}"}, status=500)

    if not chunks:
        return JsonResponse({
            "answer": "I don't have any relevant documents to answer this question. Please upload a PDF document first.",
            "sources": [],
        })

    context = "\n\n---\n\n".join(c["content"] for c in chunks)
    prompt = f"""Answer the question based ONLY on the context below.
If the answer isn't in the context, say "I don't know based on the provided documents."

Context:
{context}

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

        return JsonResponse({
            "answer": answer,
            "sources": chunks,
        })
    except requests.exceptions.ConnectionError:
        return JsonResponse(
            {
                "error": f"Could not connect to Ollama at {ollama_url}. Make sure Ollama is running (`ollama serve`)."
            },
            status=502,
        )
    except requests.exceptions.Timeout:
        return JsonResponse(
            {"error": "LLM generation timed out after 120 seconds."},
            status=504,
        )
    except Exception as e:
        return JsonResponse({"error": f"Generation error: {str(e)}"}, status=500)