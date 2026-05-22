import os
from sqlalchemy.orm import Session
from sqlalchemy import text
from dotenv import load_dotenv
from rank_bm25 import BM25Okapi
import numpy as np

load_dotenv()


def vector_search(query_embedding: list, db: Session, top_k: int = 20) -> list:
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    sql = f"""
        SELECT
            id, content, article_number, section,
            hierarchy_path, page_number, cross_references,
            1 - (embedding <=> '{embedding_str}'::vector) as similarity
        FROM chunks
        ORDER BY embedding <=> '{embedding_str}'::vector
        LIMIT {top_k}
    """

    result = db.execute(text(sql))
    return result.fetchall()


def keyword_search(query: str, db: Session, top_k: int = 20) -> list:
    all_chunks = db.execute(
        text("SELECT id, content, article_number, section, hierarchy_path, page_number, cross_references FROM chunks")
    ).fetchall()

    if not all_chunks:
        return []

    corpus = [row.content.lower().split() for row in all_chunks]
    bm25 = BM25Okapi(corpus)

    query_tokens = query.lower().split()
    scores = bm25.get_scores(query_tokens)

    top_indices = np.argsort(scores)[::-1][:top_k]
    return [(all_chunks[i], scores[i]) for i in top_indices if scores[i] > 0]


def hybrid_search(query: str, query_embedding: list, db: Session, top_k: int = 5) -> list:
    vector_results = vector_search(query_embedding, db, top_k=15)
    keyword_results = keyword_search(query, db, top_k=15)

    scored = {}

    for row in vector_results:
        scored[row.id] = {
            'chunk': row,
            'vector_score': float(row.similarity),
            'keyword_score': 0.0
        }

    max_keyword_score = max([s for _, s in keyword_results], default=1.0)
    for row, score in keyword_results:
        normalized = score / max_keyword_score if max_keyword_score > 0 else 0
        if row.id in scored:
            scored[row.id]['keyword_score'] = normalized
        else:
            scored[row.id] = {
                'chunk': row,
                'vector_score': 0.0,
                'keyword_score': normalized
            }

    for chunk_id in scored:
        v = scored[chunk_id]['vector_score']
        k = scored[chunk_id]['keyword_score']
        scored[chunk_id]['combined_score'] = (0.6 * v) + (0.4 * k)

    return sorted(scored.values(), key=lambda x: x['combined_score'], reverse=True)[:top_k]
