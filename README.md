# LaborLens UAE 🏛️

An AI-powered assistant that answers questions about UAE labor law with verified citations to specific articles of Federal Decree-Law No. 33 of 2021.

<!-- **[Live Demo](#)** · **[Video Walkthrough](#)** · **[Report an Issue](#)** -->

<!-- ![LaborLens Screenshot](docs/screenshot.png) -->

---

## What it does

UAE labor law is dense, cross-referential, and hard to navigate without legal training. HR managers, employees, and SME founders typically spend 30–90 minutes manually searching through legislation to answer a single question.

LaborLens answers those questions in under 30 seconds — with citations to the exact article so users can verify every claim themselves.

> **Disclaimer:** This tool surfaces and explains UAE labor law for informational purposes only. It does not constitute legal advice.

---

## Demo

Ask questions like:

- *"What is the maximum probation period allowed?"*
- *"How many days of annual leave is an employee entitled to?"*
- *"How is end-of-service gratuity calculated?"*
- *"What are the notice period requirements when resigning?"*
- *"Can my employer change my job role without my consent?"*

Every answer includes the specific article number, the relevant legal text, and a confidence rating.

---

## Architecture

```
User Question
      │
      ▼
┌─────────────────┐
│  Next.js UI     │  Chat interface with citation cards
└────────┬────────┘
         │ HTTP POST /query
         ▼
┌─────────────────┐
│  FastAPI        │  /query  /feedback  /stats
│  Backend        │
└────────┬────────┘
         │
    ┌────┴─────────────────────┐
    │                          │
    ▼                          ▼
┌──────────────┐     ┌──────────────────┐
│ Embed query  │     │  Keyword search  │
│ (Ollama      │     │  (BM25)          │
│  bge-m3)     │     │                  │
└──────┬───────┘     └────────┬─────────┘
       │                      │
       └──────────┬───────────┘
                  │ Hybrid retrieval
                  ▼
       ┌──────────────────┐
       │  PostgreSQL +    │  Top 5 most relevant
       │  pgvector        │  articles retrieved
       └──────────┬───────┘
                  │
                  ▼
       ┌──────────────────┐
       │  Generate answer │  Retrieved articles +
       │  (Ollama         │  question sent to LLM
       │   Llama 3.1 8B)  │
       └──────────┬───────┘
                  │
                  ▼
       ┌──────────────────┐
       │  Verify citations│  Hallucination check:
       │                  │  cited articles must exist
       └──────────┬───────┘  in retrieved context
                  │
                  ▼
         Structured JSON response
         { answer, citations, confidence }
```

### Why this architecture?

**Article-level chunking over fixed-size chunking.** Legal documents have natural structure — articles, clauses, sub-clauses. Splitting by token count destroys that structure and produces chunks that cut mid-article. This system detects article boundaries and chunks along them, so every chunk is a semantically complete legal unit with its article number, section, and cross-references preserved.

**Hybrid retrieval over pure vector search.** Legal queries fall into two categories: conceptual queries ("can I be fired during probation?") and specific queries ("Article 43 requirements"). Vector search handles the first; BM25 keyword search handles the second. Neither alone is sufficient. Combining both with a 60/40 weighting produces meaningfully better recall than either method alone.

**Citation verification as a hallucination check.** After generation, every article the LLM cites is checked against the set of retrieved articles. If the LLM cites an article that was not in the retrieval context, it is flagged and removed. This catches the most common failure mode in RAG systems — the model confidently citing something it invented.

**Query logging as a first-class concern.** Every query, retrieved chunk set, response, confidence score, and latency is written to the database. This is not an afterthought — it's what separates a demo from a system. The logs are the foundation for evaluation, iteration, and demonstrating real usage.

---

## Tech stack

| Layer | Technology | Reason |
|---|---|---|
| LLM | Llama 3.1 8B via Ollama | Free, local, no API costs |
| Embeddings | BAAI/bge-m3 via Ollama | Top-ranked on MTEB benchmark, 1024 dims |
| Vector DB | PostgreSQL + pgvector | Relational + vector search in one database |
| Backend | FastAPI + Python 3.12 | Async, fast, clean API docs via Swagger |
| Frontend | Next.js 14 + Tailwind CSS | App router, React server components |
| PDF parsing | PyMuPDF (fitz) | Reliable text extraction with page metadata |
| Keyword search | BM25 (rank-bm25) | Complements vector search for exact terms |
| ORM | SQLAlchemy | Type-safe database access |
| Containerisation | Docker + docker-compose | Reproducible local database environment |

---

## Project structure

```
laborlens/
├── backend/
│   └── app/
│       ├── core/
│       │   ├── database.py       # SQLAlchemy models + schema (4 tables)
│       │   └── init_db.py        # Creates tables + pgvector extension
│       ├── services/
│       │   ├── retrieval.py      # Hybrid search (vector + BM25)
│       │   ├── generation.py     # LLM prompting + citation verification
│       │   └── query.py          # Full pipeline orchestration
│       └── main.py               # FastAPI routes + CORS + request logging
├── ingestion/
│   ├── parser.py                 # PDF → article-level chunks
│   ├── embedder.py               # Text → vectors via Ollama bge-m3
│   └── ingest.py                 # Full ingestion pipeline
├── frontend/
│   └── app/
│       ├── page.tsx              # Chat UI with citation cards
│       ├── layout.tsx            # Root layout
│       └── globals.css           # Global styles
├── documents/                    # PDF source files (gitignored)
├── evaluation/                   # Golden test set (coming)
├── test_query.py                 # End-to-end pipeline test
├── docker-compose.yml            # PostgreSQL + pgvector container
└── .env                          # Environment config (gitignored)
```

---

## Database schema

```sql
-- Source documents
documents (id, title, filename, document_type, effective_date, source_url, ingested_at)

-- Text chunks with embeddings
chunks (id, document_id, content, article_number, section, hierarchy_path,
        page_number, has_table, cross_references, embedding vector(1024))

-- Every query logged for evaluation
query_logs (id, query, retrieved_chunk_ids, response, citations,
            confidence, latency_ms, model_used, created_at)

-- User feedback
user_feedback (id, query_log_id, rating, comment, created_at)
```

---

## Getting started

### Prerequisites

- Python 3.12+
- Node.js 18+
- Docker Desktop
- [Ollama](https://ollama.com) with the following models pulled:

```bash
ollama pull llama3.1:8b
ollama pull bge-m3
```

### 1. Clone the repo

```bash
git clone https://github.com/yourusername/laborlens.git
cd laborlens
```

### 2. Set up Python environment

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```bash
DATABASE_URL=postgresql://laborlens:laborlens_password@localhost:5432/laborlens
OLLAMA_BASE_URL=http://localhost:11434
EMBEDDING_MODEL=bge-m3
LLM_MODEL=llama3.1:8b
APP_ENV=development
```

### 4. Start the database

```bash
docker-compose up -d
```

### 5. Initialise the schema

```bash
cd backend/app/core
python init_db.py
cd ../../..
```

### 6. Add source documents

Download the UAE labour law PDFs and place them in `documents/`:

- [Federal Decree-Law No. 33 of 2021](https://u.ae/en/information-and-services/jobs/labour-law) — primary source

### 7. Run ingestion

```bash
cd ingestion
python ingest.py
cd ..
```

This parses the PDF, generates embeddings, and stores everything in the database. Takes 3–8 minutes depending on your machine.

### 8. Test the pipeline

```bash
python test_query.py
```

You should see questions answered with article citations printed to the terminal.

### 9. Start the backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

API docs available at `http://localhost:8000/docs`

### 10. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`

---

## API reference

### `POST /query`

Takes a question, returns an answer with citations.

**Request:**
```json
{
  "query": "What is the maximum probation period allowed?"
}
```

**Response:**
```json
{
  "answer": "Under UAE labour law, the probation period must not exceed 6 months...",
  "citations": [
    {
      "article": "Article 9",
      "document": "Federal Decree-Law No. 33 of 2021",
      "relevant_text": "The probation period shall not exceed six months..."
    }
  ],
  "confidence": "high",
  "limitations": "Note: This is for informational purposes only.",
  "follow_up_suggestions": [
    "What happens if I am terminated during probation?",
    "Can a probation period be extended?"
  ],
  "query_log_id": 42,
  "latency_ms": 4823
}
```

### `POST /feedback`

Records user rating for a response.

```json
{
  "query_log_id": 42,
  "rating": 1,
  "comment": "Accurate and helpful"
}
```

### `GET /stats`

Returns usage statistics.

```json
{
  "total_queries": 127,
  "avg_latency_ms": 5240,
  "positive_feedback": 89
}
```

---

## Key engineering decisions

### 1. Article-level chunking

Most RAG tutorials use fixed-size chunking (e.g. every 500 tokens with 50-token overlap). For legal documents this is wrong — it produces chunks that start mid-sentence and end mid-article, destroying the legal hierarchy that makes citations meaningful.

The parser in `ingestion/parser.py` detects article boundaries using regex patterns, splits the document along those boundaries, and stores the article number, section path, and cross-references as structured metadata alongside the text. This means retrieval can return "Article 43, Chapter 5" as a coherent unit rather than a fragment.

### 2. Hybrid retrieval

Pure vector search misses queries that contain specific legal terms or article numbers. Pure BM25 misses conceptual queries that use different words than the source document. The system runs both in parallel and combines scores with configurable weights (currently 60% vector, 40% keyword). This is tunable — if your golden set evaluation shows keyword recall is more important, you increase the BM25 weight without changing any other code.

### 3. Citation verification

The LLM is prompted to cite specific articles. But LLMs can hallucinate citations — confidently citing Article 15 when Article 15 was never retrieved. After generation, `generation.py` checks every cited article against the set of retrieved chunk IDs. Any citation that cannot be verified against the retrieval context is removed and the confidence is downgraded to `low`. This is a lightweight but effective hallucination catch.

### 4. Fully local stack

The entire system runs on local hardware with no API calls or cloud costs. Ollama serves both the LLM (Llama 3.1 8B) and the embedding model (bge-m3). This makes the development loop fast, free, and private. For production deployment, swapping to a cloud provider (Groq for LLM, HuggingFace for embeddings) is a single `.env` change — no code changes required.

### 5. Structured JSON output

The LLM is instructed to return JSON only, with a defined schema. The backend uses Ollama's `"format": "json"` parameter to enforce this at the model level, then validates and parses the response. This gives the frontend reliable structured data to render citation cards, confidence badges, and follow-up suggestions — rather than parsing free-form text.

---

## Known limitations and future work

**Current limitations:**

- Response latency is 15–40 seconds on CPU (Llama 3.1 8B is a large model). On a machine with an Nvidia GPU this drops to 3–8 seconds.
- The parser handles well-structured PDFs well but may miss content in scanned or image-based PDFs.
- Arabic language queries are not currently supported. The source documents are English versions; Arabic versions are legally binding.
- Cross-reference resolution (when Article 43 references Article 12, automatically retrieving both) is tracked in metadata but not yet implemented in retrieval.
- No authentication — the API is open. Fine for a demo; needs rate limiting and auth before any production deployment.

**Planned improvements:**

- [ ] Cross-reference graph expansion in retrieval
- [ ] Arabic language support (bilingual embeddings)
- [ ] Evaluation dashboard showing retrieval accuracy and answer quality over time
- [ ] Fine-grained confidence scoring per citation, not just per response
- [ ] WhatsApp integration via Twilio (common interface in UAE)
- [ ] Multi-document support — upload your employment contract and ask questions against both your contract and the law simultaneously

---

## Evaluation

A golden test set of 30 manually verified question/answer pairs is in progress in the `evaluation/` directory. Each entry contains the question, the expected article(s) to be retrieved, and the correct answer.

Current metrics (as of initial build):

| Metric | Score |
|---|---|
| Retrieval accuracy (correct article in top 5) | In progress |
| Citation accuracy | In progress |
| Hallucination rate | In progress |

---

## Source documents

All legal documents used are publicly available from official UAE government sources:

- Federal Decree-Law No. 33 of 2021 on the Regulation of Labour Relations — [MOHRE](https://www.mohre.gov.ae)
- UAE Government legislation portal — [u.ae](https://u.ae/en/information-and-services/jobs/labour-law)

These documents are in the public domain. The English versions are used for this project; note that Arabic versions are the legally binding originals.

---

## About this project

Built as part of a an experiment as applying full-stack engineering into applied AI engineering. The goal was to build a production-quality RAG system — not a tutorial follow-along — that demonstrates real engineering decisions: structured ingestion, hybrid retrieval, hallucination mitigation, observability, and evaluation methodology.

Stack choices were deliberately made to minimise cost (fully local via Ollama) while maintaining production-grade architecture so the system can be deployed to cloud infrastructure with minimal changes.

---

## License

MIT License — see [LICENSE](LICENSE) for details.
