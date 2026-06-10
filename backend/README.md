# Semantic Book Recommender — Backend

FastAPI backend serving 5 retrieval methods over 11,606 books.

## Quick Start

```bash
# 1. Create virtual environment
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env

# 4. Build model artifacts (first time only, ~5-10 minutes)
python scripts/init_models.py

# 5. Start server
uvicorn main:app --reload --port 8000
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/search` | Search books (tfidf, bm25, semantic, hybrid, reranking) |
| `POST` | `/search/compare` | Compare multiple methods on same query |
| `GET` | `/books/{isbn13}` | Full book detail + 7 emotion scores |
| `GET` | `/stats` | Dataset aggregate statistics |
| `GET` | `/evaluation` | Real benchmark metrics from AI pipeline |
| `GET` | `/health` | Health check |

## Architecture

```
CSV on disk (persistent) → DataFrame in RAM (runtime cache)
                         → 5 AI Retrievers (imported from AI/src/)
                         → FastAPI serves JSON API on :8000
```

Data is **read-only**. The CSV file is the source of truth. DataFrame
is re-loaded on every server restart.

## API Docs

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
