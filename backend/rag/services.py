import requests
from django.conf import settings
from pdfminer.high_level import extract_text
from langchain_text_splitters import RecursiveCharacterTextSplitter


def extract_text_from_pdf(file_obj) -> str:
    """
    Extract raw text from an uploaded PDF file stream or object.
    """
    try:
        if hasattr(file_obj, "seek"):
            file_obj.seek(0)
        elif hasattr(file_obj, "file") and hasattr(file_obj.file, "seek"):
            file_obj.file.seek(0)
        target = getattr(file_obj, "file", file_obj)
        text = extract_text(target)
        return (text or "").strip()
    except Exception as e:
        raise ValueError(f"Failed to extract text from PDF: {str(e)}")


def chunk_text(text: str, chunk_size: int = 800, chunk_overlap: int = 150) -> list[str]:
    """
    Split text into chunks with overlap for embedding.
    """
    if not text or not text.strip():
        return []
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    return splitter.split_text(text)


def embed(text: str) -> list[float]:
    """
    Generate an embedding vector for a piece of text using Ollama.
    Requires Ollama running and the embedding model pulled (e.g. nomic-embed-text).
    """
    ollama_url = getattr(settings, "OLLAMA_URL", "http://localhost:11434")
    model = getattr(settings, "OLLAMA_EMBED_MODEL", "nomic-embed-text")

    try:
        response = requests.post(
            f"{ollama_url}/api/embeddings",
            json={"model": model, "prompt": text},
            timeout=60,
        )
        if response.status_code != 200:
            error_msg = response.text
            try:
                error_msg = response.json().get("error", response.text)
            except Exception:
                pass
            raise RuntimeError(f"Ollama error ({response.status_code}): {error_msg}")

        data = response.json()
        if "embedding" not in data:
            raise ValueError(f"Ollama response missing 'embedding' field: {data}")
        return data["embedding"]
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            f"Could not connect to Ollama at {ollama_url}. Make sure Ollama is running (`ollama serve`)."
        )
    except requests.exceptions.Timeout:
        raise RuntimeError("Ollama embedding request timed out.")
    except Exception as e:
        raise RuntimeError(str(e))
