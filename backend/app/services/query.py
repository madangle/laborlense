import time
import sys
sys.path.append('../..')

from openai import OpenAI
import requests
import os
from dotenv import load_dotenv

load_dotenv()

from app.services.retrieval import hybrid_search
from app.services.generation import generate_answer

# openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "bge-m3")

def embed_query(query: str) -> list:
    """Embed query using local Ollama bge-m3"""
    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/embeddings",
        json={
            "model": EMBEDDING_MODEL,
            "prompt": query.replace('\n', ' ').strip()
        }
    )
    return response.json()["embedding"]


def answer_query(query: str, db) -> dict:
    """
    Full pipeline: query → embed → retrieve → generate → return
    """
    start_time = time.time()
    
    print(f"\n🔍 Query: {query}")
    
    # Step 1: Embed the query
    print("  → Embedding query...")
    query_embedding = embed_query(query)
    
    # Step 2: Retrieve relevant chunks
    print("  → Retrieving relevant chunks...")
    retrieved_chunks = hybrid_search(query, query_embedding, db, top_k=5)
    print(f"  → Found {len(retrieved_chunks)} relevant chunks")
    
    for i, item in enumerate(retrieved_chunks, 1):
        print(f"     {i}. {item['chunk'].article_number} (score: {item['combined_score']:.3f})")
    
    # Step 3: Generate answer
    print("  → Generating answer...")
    result = generate_answer(query, retrieved_chunks)
    
    # Step 4: Add metadata
    end_time = time.time()
    result['latency_ms'] = int((end_time - start_time) * 1000)
    result['retrieved_articles'] = [
        item['chunk'].article_number 
        for item in retrieved_chunks
    ]
    
    print(f"  → Done in {result['latency_ms']}ms")
    
    return result