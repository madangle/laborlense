# ingestion/embedder.py — Ollama version

import requests
import time
import os
from dotenv import load_dotenv

load_dotenv('../.env')

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "bge-m3")


def get_embedding(text: str) -> list[float]:
    """
    Get embedding vector from Ollama (local, free).
    bge-m3 produces 1024-dimensional vectors.
    """
    text = text.replace('\n', ' ').strip()

    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/embeddings",
        json={
            "model": EMBEDDING_MODEL,
            "prompt": text
        }
    )

    if response.status_code != 200:
        raise Exception(f"Ollama embedding error: {response.text}")

    return response.json()["embedding"]


def get_embeddings_batch(texts: list[str], batch_size: int = 10) -> list[list[float]]:
    """
    Embed multiple texts one by one.
    Ollama doesn't support batch embedding, so we loop.
    We use a smaller batch_size than before since this is local.
    """
    all_embeddings = []

    for i, text in enumerate(texts):
        embedding = get_embedding(text)
        all_embeddings.append(embedding)

        # Progress update every 10 chunks
        if (i + 1) % 10 == 0:
            print(f"  Embedded {i+1}/{len(texts)} chunks...")

        # Small pause to not overwhelm local Ollama
        time.sleep(0.1)

    print(f"  Done — embedded all {len(texts)} chunks")
    return all_embeddings