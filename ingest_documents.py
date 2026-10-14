
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not DATABASE_URL or not GEMINI_API_KEY:
    raise RuntimeError("Set DATABASE_URL and GEMINI_API_KEY in .env")

client = genai.Client(api_key=GEMINI_API_KEY)

EMBED_MODEL = "gemini-embedding-001"
EMBED_DIMENSIONS = 768


def read_document(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    if path.suffix.lower() in {".txt", ".md"}:
        return path.read_text(encoding="utf-8")

    return ""


def split_text(text: str, chunk_size: int = 1200, overlap: int = 200):
    text = " ".join(text.split())
    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end == len(text):
            break

        start = end - overlap

    return chunks


def embed_text(text: str) -> list[float]:
    response = client.models.embed_content(
        model=EMBED_MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=EMBED_DIMENSIONS,
        ),
    )
    return list(response.embeddings[0].values)


def main():
    folder = BASE_DIR / "documents"
    files = [
        path for path in folder.rglob("*")
        if path.is_file()
        and path.suffix.lower() in {".pdf", ".txt", ".md"}
    ]

    if not files:
        print("No documents found. Add a PDF, TXT, or MD file to documents/.")
        return

    with psycopg.connect(DATABASE_URL) as conn:
        for path in files:
            text = read_document(path)

            if not text.strip():
                print(f"Skipping empty/unreadable file: {path.name}")
                continue

            chunks = split_text(text)

            for chunk in chunks:
                embedding = embed_text(chunk)
                vector_literal = "[" + ",".join(map(str, embedding)) + "]"

                conn.execute(
                    """
                    INSERT INTO knowledge_chunks
                        (source, chunk_text, embedding)
                    VALUES (%s, %s, %s::vector)
                    """,
                    (path.name, chunk, vector_literal),
                )

            print(f"Indexed {len(chunks)} chunks from {path.name}")

    print("Document ingestion complete.")


if __name__ == "__main__":
    main()
