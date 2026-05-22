from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
import sys, os, time
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(__file__))

from app.core.database import get_db, QueryLog, UserFeedback
from app.services.query import answer_query

app = FastAPI(
    title="LaborLens UAE API",
    description="UAE Labor Law Intelligence Assistant",
    version="1.0.0"
)

# Allow requests from your frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://your-vercel-url.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response Models ─────────────────────────────────────

class QueryRequest(BaseModel):
    query: str
    conversation_history: list = []  # for follow-up questions

class FeedbackRequest(BaseModel):
    query_log_id: int
    rating: int   # 1 = helpful, -1 = not helpful
    comment: str = ""


# ── Routes ────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "ok", "service": "LaborLens UAE API"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/query")
def query_endpoint(request: QueryRequest, db: Session = Depends(get_db)):
    """
    Main endpoint: takes a question, returns answer with citations.
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    if len(request.query) > 1000:
        raise HTTPException(status_code=400, detail="Query too long (max 1000 chars)")
    
    start = time.time()
    
    # Get answer from pipeline
    result = answer_query(request.query, db)
    
    latency_ms = int((time.time() - start) * 1000)
    
    # Log the query for evaluation and analytics
    log = QueryLog(
        query=request.query,
        retrieved_chunk_ids=result.get('retrieved_articles', []),
        response=result.get('answer', ''),
        citations=result.get('citations', []),
        confidence=result.get('confidence', ''),
        latency_ms=latency_ms,
        model_used="claude-sonnet-4-20250514"
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    
    result['query_log_id'] = log.id
    result['latency_ms'] = latency_ms
    
    return result


@app.post("/feedback")
def feedback_endpoint(request: FeedbackRequest, db: Session = Depends(get_db)):
    """Stores user thumbs up/down feedback"""
    feedback = UserFeedback(
        query_log_id=request.query_log_id,
        rating=request.rating,
        comment=request.comment
    )
    db.add(feedback)
    db.commit()
    return {"status": "recorded", "message": "Thank you for your feedback"}


@app.get("/stats")
def stats_endpoint(db: Session = Depends(get_db)):
    """Basic usage stats for your dashboard"""
    from sqlalchemy import text, func
    from core.database import QueryLog, UserFeedback
    
    total_queries = db.query(QueryLog).count()
    avg_latency = db.query(func.avg(QueryLog.latency_ms)).scalar()
    positive_feedback = db.query(UserFeedback).filter(UserFeedback.rating == 1).count()
    
    return {
        "total_queries": total_queries,
        "avg_latency_ms": round(avg_latency or 0, 1),
        "positive_feedback": positive_feedback
    }