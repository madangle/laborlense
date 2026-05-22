from sqlalchemy import create_engine, Column, String, Integer, Text, Boolean, DateTime, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pgvector.sqlalchemy import Vector
from datetime import datetime
import os
from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Document(Base):
    """Stores each source PDF document"""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    document_type = Column(String)  # "law", "resolution", "circular"
    effective_date = Column(String)
    source_url = Column(String)
    ingested_at = Column(DateTime, default=datetime.utcnow)


class Chunk(Base):
    """Stores individual text chunks with their embeddings"""
    __tablename__ = "chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)       # the actual text
    article_number = Column(String)              # e.g. "Article 43"
    section = Column(String)                     # e.g. "Chapter 5"
    hierarchy_path = Column(String)              # e.g. "Chapter 5 > Article 43 > Clause 2"
    page_number = Column(Integer)
    has_table = Column(Boolean, default=False)
    cross_references = Column(JSON, default=list) # ["Article 12", "Article 7"]
    embedding = Column(Vector(1024))             # NEW — bge-m3 dimensions


class QueryLog(Base):
    """Logs every user query for evaluation and analytics"""
    __tablename__ = "query_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    query = Column(Text, nullable=False)
    retrieved_chunk_ids = Column(JSON)
    response = Column(Text)
    citations = Column(JSON)
    confidence = Column(String)
    latency_ms = Column(Integer)
    model_used = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserFeedback(Base):
    """Stores thumbs up/down feedback from users"""
    __tablename__ = "user_feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    query_log_id = Column(Integer, nullable=False)
    rating = Column(Integer)  # 1 = thumbs up, -1 = thumbs down
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


def create_tables():
    """Create all tables and enable pgvector extension"""
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")


def get_db():
    """Dependency for FastAPI routes"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()