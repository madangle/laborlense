# backend/app/services/generation.py — Ollama version

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.1:8b")


SYSTEM_PROMPT = """You are a UAE Labor Law Information Assistant.

Your job is to answer questions about UAE labor law using ONLY the legal articles provided to you.

STRICT RULES:
1. Use ONLY the provided context. Never use outside knowledge.
2. Cite the specific article number for every claim.
3. If context is insufficient, say: "I cannot find sufficient information in the provided law to answer this."
4. Never give legal advice. You explain the law only.
5. Always end with: "Note: This is for informational purposes only and does not constitute legal advice."

YOU MUST RESPOND WITH VALID JSON ONLY. No text before or after the JSON.

Use exactly this format:
{
  "answer": "your explanation here",
  "citations": [
    {
      "article": "Article X",
      "document": "Federal Decree-Law No. 33 of 2021",
      "relevant_text": "brief summary of the relevant provision"
    }
  ],
  "confidence": "high",
  "limitations": "any caveats here",
  "follow_up_suggestions": ["question 1", "question 2"]
}"""


def build_context_block(retrieved_chunks: list) -> str:
    """Format retrieved chunks for the prompt"""
    context_parts = []

    for i, item in enumerate(retrieved_chunks, 1):
        chunk = item['chunk']
        context_parts.append(f"""
--- LEGAL CONTEXT {i} ---
Article: {chunk.article_number}
Section: {chunk.section}
Content:
{chunk.content}
""")

    return '\n'.join(context_parts)


def verify_citations(response_json: dict, retrieved_chunks: list) -> dict:
    """Check cited articles actually appeared in retrieved context"""
    if 'citations' not in response_json:
        return response_json

    retrieved_articles = set()
    for item in retrieved_chunks:
        chunk = item['chunk']
        if chunk.article_number:
            retrieved_articles.add(chunk.article_number.lower())

    verified = []
    unverified = []

    for citation in response_json['citations']:
        article_ref = citation.get('article', '').lower()
        if any(article_ref in r or r in article_ref for r in retrieved_articles):
            verified.append(citation)
        else:
            unverified.append(citation.get('article', 'Unknown'))

    response_json['citations'] = verified

    if unverified:
        response_json['limitations'] = (
            response_json.get('limitations', '') +
            f" [Unverified citations removed: {', '.join(unverified)}]"
        )
        response_json['confidence'] = 'low'

    return response_json


def generate_answer(query: str, retrieved_chunks: list) -> dict:
    """
    Generate answer using local Ollama LLM.
    
    Key difference from Claude: Ollama is slower (15-40s on CPU)
    and sometimes needs more explicit JSON instructions for smaller models.
    """
    context = build_context_block(retrieved_chunks)

    # For local models, we put the system prompt inside the user message
    # because some Ollama models handle system prompts inconsistently
    full_prompt = f"""{SYSTEM_PROMPT}

LEGAL CONTEXT TO USE:
{context}

USER QUESTION:
{query}

Respond with JSON only. No text outside the JSON object."""

    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json={
            "model": LLM_MODEL,
            "prompt": full_prompt,
            "stream": False,          # wait for full response
            "format": "json",         # Ollama's built-in JSON mode
            "options": {
                "temperature": 0.1,   # low = more consistent, less creative
                "num_predict": 1000   # max tokens to generate
            }
        },
        timeout=120  # local models can be slow — wait up to 2 minutes
    )

    if response.status_code != 200:
        raise Exception(f"Ollama generation error: {response.text}")

    raw_text = response.json()["response"].strip()

    # Parse JSON response
    try:
        # Clean up common model output issues
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]

        result = json.loads(raw_text.strip())

    except json.JSONDecodeError:
        # Fallback if model doesn't return clean JSON
        result = {
            "answer": raw_text,
            "citations": [],
            "confidence": "low",
            "limitations": "Response format issue — the model did not return structured JSON.",
            "follow_up_suggestions": []
        }

    result = verify_citations(result, retrieved_chunks)
    return result