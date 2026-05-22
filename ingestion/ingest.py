import os
import sys
sys.path.append('./backend')

from dotenv import load_dotenv
load_dotenv('./.env')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from parser import parse_legal_pdf
from embedder import get_embeddings_batch

# Import models
sys.path.append('./backend/app/core')
from database import Document, Chunk, Base, engine

SessionLocal = sessionmaker(bind=engine)


def ingest_document(
    filepath: str,
    title: str,
    document_type: str = "law",
    effective_date: str = "",
    source_url: str = ""
):
    """
    Full ingestion pipeline:
    1. Parse PDF into chunks
    2. Generate embeddings
    3. Store everything in the database
    """
    print(f"\n🚀 Starting ingestion: {title}")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Step 1: Create document record
        print("\n📄 Step 1: Creating document record...")
        document = Document(
            title=title,
            filename=os.path.basename(filepath),
            document_type=document_type,
            effective_date=effective_date,
            source_url=source_url
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        print(f"  Document ID: {document.id}")
        
        # Step 2: Parse PDF
        print("\n📖 Step 2: Parsing PDF...")
        chunks = parse_legal_pdf(filepath, title)
        print(f"  Found {len(chunks)} chunks")
        
        # Step 3: Generate embeddings
        print(f"\n🔢 Step 3: Generating embeddings for {len(chunks)} chunks...")
        texts = [chunk.content for chunk in chunks]
        embeddings = get_embeddings_batch(texts)
        print(f"  Generated {len(embeddings)} embeddings")
        
        # Step 4: Store chunks with embeddings
        print("\n💾 Step 4: Storing chunks in database...")
        
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            db_chunk = Chunk(
                document_id=document.id,
                content=chunk.content,
                article_number=chunk.article_number,
                section=chunk.section,
                hierarchy_path=chunk.hierarchy_path,
                page_number=chunk.page_number,
                has_table=chunk.has_table,
                cross_references=chunk.cross_references,
                embedding=embedding
            )
            db.add(db_chunk)
            
            # Commit in batches of 50
            if (i + 1) % 50 == 0:
                db.commit()
                print(f"  Saved {i+1}/{len(chunks)} chunks...")
        
        db.commit()
        
        print(f"\n✅ Ingestion complete!")
        print(f"  Document: {title}")
        print(f"  Chunks stored: {len(chunks)}")
        print(f"  Document ID: {document.id}")
        
        return document.id
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error during ingestion: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    ingest_document(
        filepath="./documents/federal_decree_law_33_2021.pdf",
        title="Federal Decree-Law No. 33 of 2021 — Regulation of Labour Relations",
        document_type="law",
        effective_date="2022-02-02",
        source_url="https://u.ae/en/information-and-services/jobs/labour-law"
    )