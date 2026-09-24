import logging
import os
import requests
import pdfplumber
from django.conf import settings
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from rag.models import Document

load_dotenv()

logger = logging.getLogger(__name__)

# Global lazy-loaded embedding model instance (if using local FlagEmbedding)
_bge_model = None


def get_local_embed_model():
    """
    Lazily loads the local BGE-M3 embedding model if FlagEmbedding is installed.
    """
    global _bge_model
    if _bge_model is None:
        try:
            from FlagEmbedding import BGEM3FlagModel
            logger.info("Loading local BGEM3FlagModel...")
            _bge_model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=False)
        except Exception as e:
            logger.warning(f"Could not load local BGEM3FlagModel: {e}")
            _bge_model = False
    return _bge_model if _bge_model is not False else None

def rerank(query: str, candidates: list[dict], top_k: int = 5) -> tuple[list[dict], bool]:
    """
    Reranks candidate chunks using Jina Reranker v2.
    Returns (chunks, reranked_flag).
    - chunks: top_k chunks, ordered by rerank score (or vector score on failure)
    - reranked_flag: True if Jina actually reranked; False if we fell back
    """
    if not candidates:
        return [], False

    api_key = os.getenv("JINA_API_KEY")
    if not api_key:
        logger.warning("JINA_API_KEY not found. Returning top vector candidates without reranking.")
        return candidates[:top_k], False

    try:
        resp = requests.post(
            "https://api.jina.ai/v1/rerank",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "jina-reranker-v2-base-multilingual",
                "query": query,
                "documents": [c["content"] for c in candidates],
                "top_n": min(top_k, len(candidates)),
            },
            timeout=8,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])

        reranked = []
        for r in results:
            idx = r["index"]
            c = dict(candidates[idx])
            c["rerank_score"] = round(float(r.get("relevance_score", 0.0)), 4)
            reranked.append(c)

        if reranked:
            return reranked, True
        return candidates[:top_k], False

    except requests.exceptions.Timeout as e:
        logger.warning(f"Jina rerank timed out: {e}. Falling back.")
        return candidates[:top_k], False
    except requests.exceptions.HTTPError as e:
        logger.error(f"Jina rerank HTTP error: {e}. Falling back.")
        return candidates[:top_k], False
    except Exception as e:
        logger.error(f"Jina rerank unexpected failure: {e}", exc_info=True)
        return candidates[:top_k], False

        
def extract_tables_and_text(pdf_file):
    """
    Returns (plain_text_chunks_source, flattened_table_sentences)
    Tables are extracted and converted to standalone sentences;
    remaining prose is returned separately for chunking.
    """
    full_text_parts = []
    table_sentences = []

    if hasattr(pdf_file, "seek"):
        pdf_file.seek(0)
    elif hasattr(pdf_file, "file") and hasattr(pdf_file.file, "seek"):
        pdf_file.file.seek(0)
    target = getattr(pdf_file, "file", pdf_file)

    with pdfplumber.open(target) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            tables = page.find_tables()
            table_bboxes = [t.bbox for t in tables]

            # Extract and flatten each detected table
            for table in tables:
                rows = table.extract()
                if not rows or len(rows) < 2:
                    continue
                header = [str(h).strip() if h else "" for h in rows[0]]
                for row in rows[1:]:
                    row = [str(c).strip() if c else "" for c in row]
                    if not any(row):
                        continue
                    label = row[0]
                    pairs = [
                        f"{header[i]} scored {row[i]}"
                        for i in range(1, len(row))
                        if row[i]
                    ]
                    sentence = f"On {label}, " + ", ".join(pairs) + "."
                    table_sentences.append(sentence)

            # Extract non-table text on this page, excluding table regions
            page_text = page.filter(
                lambda obj: not any(
                    bbox[0] <= obj.get("x0", -1) <= bbox[2]
                    and bbox[1] <= obj.get("top", -1) <= bbox[3]
                    for bbox in table_bboxes
                )
            ).extract_text() or ""
            full_text_parts.append(page_text)

    return "\n\n".join(full_text_parts), table_sentences


def chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> list[str]:
    """
    Split text into manageable chunks with overlap for embedding.
    """
    if not text or not text.strip():
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_text(text)
    return [c.strip() for c in chunks if c.strip()]


def embed(text: str) -> list[float]:
    """
    Generate an embedding vector for a piece of text.
    Tries local BGEM3FlagModel if loaded; otherwise calls Ollama embeddings API.
    """
    if not text or not text.strip():
        return [0.0] * 1024

    # 1. Try local BGE model if available
    local_model = get_local_embed_model()
    if local_model is not None:
        try:
            response = local_model.encode(
                [text],
                return_dense=True,
                return_sparse=False,
                return_colbert_vecs=False,
            )
            return response["dense_vecs"][0].tolist()
        except Exception as e:
            logger.warning(f"Local BGEM3 encoding failed: {e}. Trying Ollama...")

    # 2. Try Ollama embeddings endpoint
    ollama_url = getattr(settings, "OLLAMA_URL", "http://localhost:11434")
    embed_model = getattr(settings, "OLLAMA_EMBED_MODEL", "bge-m3")

    try:
        res = requests.post(
            f"{ollama_url}/api/embeddings",
            json={"model": embed_model, "prompt": text},
            timeout=30,
        )
        if res.status_code == 200:
            vec = res.json().get("embedding")
            if vec and isinstance(vec, list):
                return vec
    except Exception as e:
        logger.warning(f"Ollama /api/embeddings failed: {e}")

    try:
        res = requests.post(
            f"{ollama_url}/api/embed",
            json={"model": embed_model, "input": text},
            timeout=30,
        )
        if res.status_code == 200:
            embeddings = res.json().get("embeddings", [])
            if embeddings and len(embeddings) > 0:
                return embeddings[0]
    except Exception as e:
        logger.warning(f"Ollama /api/embed failed: {e}")

    raise RuntimeError(
        f"Could not generate embedding for text. Ensure Ollama is running at {ollama_url} with model '{embed_model}' or BGEM3FlagModel is available."
    )


def ingest_pdf(file_obj, chat, title, source_id):
    """
    Full pipeline: extract prose and tables, chunk prose, vectorize all, and store in DB.
    """
    plain_text, table_sentences = extract_tables_and_text(file_obj)

    # Normal prose gets token-aware chunking
    prose_chunks = chunk_text(plain_text)

    # Table rows are kept as standalone sentences
    all_chunks = prose_chunks + table_sentences

    created_docs = []
    for i, chunk in enumerate(all_chunks):
        doc = Document.objects.create(
            chat=chat,
            title=title,
            content=chunk,
            embedding=embed(chunk),
            source_id=source_id,
            chunk_index=i,
        )
        created_docs.append(doc)
    return all_chunks


def derive_chat_title(file_obj, fallback_title: str = "New Chat") -> str:
    """
    Derives a short, descriptive title for a chat from the first page of a PDF.
    Gracefully falls back to fallback_title or PDF header if LLM is unavailable.
    """
    first_lines = ""
    try:
        if hasattr(file_obj, "seek"):
            file_obj.seek(0)
        elif hasattr(file_obj, "file") and hasattr(file_obj.file, "seek"):
            file_obj.file.seek(0)
        reader = PdfReader(file_obj)
        if reader.pages:
            text = reader.pages[0].extract_text() or ""
            non_empty_lines = [line.strip() for line in text.split("\n") if line.strip()]
            if non_empty_lines:
                first_lines = " ".join(non_empty_lines[:4])
    except Exception as e:
        logger.warning(f"Could not read PDF first page for title: {e}")

    if not first_lines:
        return fallback_title[:80].strip() or "New Chat"

    ollama_url = getattr(settings, "OLLAMA_URL", "http://localhost:11434")
    model = getattr(settings, "OLLAMA_LLM_MODEL", "gemma4:31b-cloud")

    try:
        prompt = (
            f"Generate a short 3 to 6 word title for a document that starts with: '{first_lines[:300]}'.\n"
            "Respond ONLY with the title. Do not add quotes or markdown."
        )
        res = requests.post(
            f"{ollama_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=10,
        )
        if res.status_code == 200:
            answer = res.json().get("response", "").strip().strip('"\'')
            if answer:
                return answer[:80].strip()
    except Exception as e:
        logger.info(f"Ollama title generation skipped/failed ({e}), using fallback.")

    cleaned_line = first_lines[:50].strip()
    return cleaned_line if cleaned_line else fallback_title[:50].strip()