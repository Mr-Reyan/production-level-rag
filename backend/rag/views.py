from django.shortcuts import render
from rest_framework.decorators import api_view
from django.views.decorators.csrf import csrf_exempt
from .models import Document
import json
from .services import embed
from django.http import JsonResponse
from django.db import connection
import uuid
from .services import chunk_text,extract_text_from_pdf

@api_view(['POST'])
def add_document(request):
    body = json.loads(request.body)
    doc = Document.objects.create(
        title=body['title'],
        content=body['content'],
        embedding=embed(body['content']),
    )
    return JsonResponse({'id':doc.id,'title':doc.title})

@api_view(['POST'])
def search(request):
    body = json.loads(request.body)
    query_vector = embed(body['query'])
    top_k = body.get("top_k", 5)

    with connection.cursor() as cur:
        cur.execute(
            'select id, content, similarity from match_documents(%s::vector,%s)',
            [query_vector,top_k],
        )
        rows = cur.fetchall()

    results = [{'id':r[0], 'content':r[1], 'similarity':r[2]} for r in rows]

    return JsonResponse({'results':results})

@api_view(['POST'])
def upload_pdf(request):
    pdf_file = request.FILES['file']
    source_id=uuid.uuid4()

    text = extract_text_from_pdf(pdf_file)
    chunks = chunk_text(text)

    for i, chunk in enumerate(chunks):
        Document.objects.create(
            title=pdf_file.name,
            content=chunk,
            embedding=embed(chunk),
            source_id=source_id,
            chunk_index=i,
        )

    return JsonResponse({'source_id':str(source_id),'chunks':len(chunks)})


import requests
from django.db import connection
from django.conf import settings

@csrf_exempt
def ask(request):
    body = json.loads(request.body)
    question = body['question']

    query_vector = embed(question)
    with connection.cursor() as c:
        c.execute(
            'select id,content, source_id, similarity from match_documents(%s::vector,%s)',
            [query_vector,5]
        )
        rows = c.fetchall()

    chunks = [{"id": r[0], "content": r[1], "source_id": str(r[2]), "similarity": r[3]} for r in rows]

    context = "\n\n---\n\n".join(c["content"] for c in chunks)
    prompt = f"""Answer the question based ONLY on the context below.
    If the answer isn't in the context, say "I don't know based on the provided documents."

    Context:
    {context}

    Question: {question}
    Answer:"""


    llm_response = requests.post(
        f"{settings.OLLAMA_URL}/api/generate",
        json={"model": "gemma4:31b-cloud", "prompt": prompt, "stream": False},
        timeout=120,
    ).json()
    print("OLLAMA RAW:", llm_response)
    return JsonResponse({
        "answer": llm_response["response"],
        "sources": chunks,
    })