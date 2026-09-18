import requests
from django.conf import settings
from pdfminer.high_level import extract_text
from langchain_text_splitters import RecursiveCharacterTextSplitter

def extract_text_from_pdf(file_obj: str) -> str:
    return extract_text(file_obj.file)


def chunk_text(text: str, chunk_size: int = 800, chunk_overlap: int = 150) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    return splitter.split_text(text)

def embed(text: str) -> list[float]:
    """
    Generate a 768-dim embedding for a piece of text using Ollama + Nomic.
    Requires `ollama serve` running and `ollama pull nomic-embed-text`.
    """
    ollama_url = getattr(settings, "OLLAMA_URL", "http://localhost:11434")
    response = requests.post(
        f"{ollama_url}/api/embeddings",
        json={"model": "nomic-embed-text", "prompt": text},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["embedding"]

