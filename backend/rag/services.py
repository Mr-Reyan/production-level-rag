import requests
from django.conf import settings
from pdfminer.high_level import extract_text
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader


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


def derive_chat_title(file_obj) -> str:
    try:
        reader = PdfReader(file_obj)
        page = reader.pages[0]
        text = page.extract_text()
        lines = text.split("\n")
        joined = ".".join(lines)

        prompt = (
            "Generate a title for a chat based on some starting lines of the PDF: "
            f"{joined}\n"
            "If you don't understand what to derive as a title, keep it general "
            "and based on the lines. Don't exceed 100 characters. Keep it short "
            "and simple. Only respond with the title — nothing else, no preamble."
        )

        ollama_url = "http://localhost:11434"
        model = "gemma4:31b-cloud"

        res = requests.post(
            f"{ollama_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=120,
        )
        res.raise_for_status()

        answer = res.json().get("response", "").strip()
        if not answer:
            return "Untitled chat"

        return answer[:100].strip()

    except Exception as e:
        raise RuntimeError(f"Failed to derive chat title: {e}")


from transformers import AutoTokenizer

# _tokenizer = AutoTokenizer.from_pretrained("BAAI/bge-m3")


def chunk_text(text: str, chunk_size: int = 512, chunk_overlap: int = 50) -> list[str]:
    """
    Split text into chunks with overlap for embedding.
    """

    if not text or not text.strip():
        return []
    splitter = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
        _tokenizer,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return splitter.split_text(text)


from FlagEmbedding import BGEM3FlagModel

# _model = BGEM3FlagModel('BAAI/bge-m3', use_fp16=True)


def embed(text: str) -> list[float]:
    """
    Generate an embedding vector for a piece of text using Ollama.
    Requires Ollama running and the embedding model pulled (e.g. nomic-embed-text).
    """

    try:
        response = _model.encode(
            [f"{text}"],
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False,
        )

        return response["dense_vecs"][0].tolist()

    except Exception as e:
        raise RuntimeError(str(e))
