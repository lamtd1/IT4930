# 📚 Book Retrieval Benchmark

A **production-ready** Python benchmark for evaluating and comparing book retrieval systems.

Designed for university research, portfolio projects, and IR benchmarking.

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                        CLI  (src/main.py)                      │
│              build-indexes │ build-ground-truth │ evaluate     │
└───────────────────┬────────────────┬────────────────┬──────────┘
                    │                │                │
          ┌─────────▼──────┐ ┌───────▼──────┐ ┌──────▼───────────┐
          │ build_indexes  │ │ build_ground │ │evaluate_retrievers│
          │   pipeline     │ │truth pipeline│ │    pipeline       │
          └────────────────┘ └──────┬───────┘ └──────┬────────────┘
                                    │                 │
                         ┌──────────▼──────────┐      │
                         │    LLM Chains        │      │
                         │  QueryGeneration     │      │
                         │  RelevanceJudge      │      │
                         └──────────┬──────────┘      │
                                    │                  │
                         ┌──────────▼──────────────────▼────────┐
                         │          Retrieval Layer              │
                         │  TF-IDF  BM25  Dense  Hybrid  Rerank │
                         └───────────────────────────────────────┘
                                    │
                         ┌──────────▼──────────┐
                         │   Evaluation Layer   │
                         │  Metrics  Evaluator  │
                         └─────────────────────┘
```

---

## 🔬 Retrievers Compared

| Retriever | Method | Notes |
|---|---|---|
| **TF-IDF** | Cosine similarity in TF-IDF space | scikit-learn |
| **BM25** | Probabilistic term weighting | rank-bm25 |
| **Dense** | Bi-encoder semantic embeddings | SentenceTransformers + ChromaDB |
| **Hybrid RRF** | Reciprocal Rank Fusion (BM25 + Dense) | Configurable candidate pool & weights |
| **Reranking** | Dense recall + Cross-Encoder reranking | Two-stage pipeline |

---

## 📋 Evaluation Metrics

| Metric | Description |
|---|---|
| **P@5** | Precision at rank 5 |
| **P@10** | Precision at rank 10 |
| **R@5** | Recall at rank 5 |
| **R@10** | Recall at rank 10 |
| **MRR** | Mean Reciprocal Rank |
| **NDCG@10** | Normalised Discounted Cumulative Gain |
| **MAP** | Mean Average Precision |
| **Latency (ms)** | Average query response time |

---

## 📁 Project Structure

```
book-retrieval-benchmark/
│
├── .env.example              # Environment variable template
├── requirements.txt          # Direct dependencies
│
├── data/
│   ├── raw/                  # Original CSV dataset
│   ├── processed/            # Cleaned books_clean.csv
│   └── eval/                 # qrels.json + evaluation_results.json
│
├── models/                   # Persisted indexes (auto-created)
│   ├── tfidf.pkl
│   ├── tfidf_matrix.npz
│   └── bm25.pkl
│
├── logs/                     # Rotating log files (auto-created)
│
├── src/
│   ├── config/
│   │   └── settings.py       # Pydantic-Settings – ALL configuration
│   │
│   ├── schemas/
│   │   ├── query.py          # BookInfo, BookQueries, BatchQueryResponse
│   │   ├── relevance.py      # RelevanceScore, BookRelevance
│   │   ├── benchmark.py      # QrelItem, BenchmarkResult, EvalSummary
│   │   └── retrieval.py      # RetrievalResult, RetrievalResultList
│   │
│   ├── chains/
│   │   ├── query_generation_chain.py   # Batch query generation (LLM)
│   │   └── relevance_judge_chain.py    # LLM-as-judge relevance scoring
│   │
│   ├── retrieval/
│   │   ├── base.py                     # BaseRetriever ABC
│   │   ├── tfidf_retriever.py
│   │   ├── bm25_retriever.py
│   │   ├── dense_retriever.py
│   │   ├── hybrid_rrf_retriever.py
│   │   └── rerank_retriever.py
│   │
│   ├── services/
│   │   ├── query_service.py     # Batch query orchestration
│   │   ├── judge_service.py     # Relevance judging + caching
│   │   └── candidate_service.py # Dense-only GT candidate retrieval
│   │
│   ├── evaluation/
│   │   ├── metrics.py           # Pure IR metric functions
│   │   └── evaluator.py         # Runs all retrievers × all queries
│   │
│   ├── pipelines/
│   │   ├── build_indexes.py
│   │   ├── build_ground_truth.py
│   │   └── evaluate_retrievers.py
│   │
│   ├── utils/
│   │   ├── logging_config.py    # Rotating file + console logging
│   │   └── text_utils.py        # clean_text, build_corpus_text, BGE prefix
│   │
│   └── main.py                  # Typer CLI entry point
│
└── tests/
    ├── conftest.py
    ├── test_metrics.py
    ├── test_query_generation.py
    ├── test_relevance_judge.py
    ├── test_retrievers.py
    └── test_evaluator.py
```

---

## ⚙️ Installation

### 1. Clone and set up virtual environment

```bash
cd "....\AI"
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux / macOS
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
copy .env.example .env
```

Edit `.env` and set at minimum:

```env
OPENAI_API_KEY=sk-...
```

> **Tip**: Set `MAX_BOOKS_TO_PROCESS=50` and `QUERIES_PER_BOOK=1` for a fast dry run.

---

## 🚀 Pipeline Execution

### Step 1 – Build Retrieval Indexes

Processes the dataset and builds TF-IDF, BM25, and ChromaDB indexes.

```bash
python -m src.main build-indexes
```

**Prerequisites**: `data/processed/books_clean.csv` must exist  
**Creates**: `models/tfidf.pkl`, `models/tfidf_matrix.npz`, `models/bm25.pkl`, `data/chroma_db/`

---

### Step 2 – Build Ground Truth

Generates evaluation queries via LLM, retrieves dense candidates, and uses LLM-as-judge to create `qrels.json`.

```bash
python -m src.main build-ground-truth
```

**Prerequisites**: Step 1 complete + `OPENAI_API_KEY` set  
**Creates**: `data/eval/qrels.json`

> ⚠️ **Cost Warning**: This step calls OpenAI for every (query, candidate) pair.  
> Control costs with the flags below or via the `.env` equivalents.

#### CLI Parameter Overrides

Các flag sau cho phép ghi đè giá trị `.env` **trực tiếp từ dòng lệnh** mà không cần sửa file:

| Flag | `.env` equivalent | Default | Mô tả |
|---|---|---|---|
| `--pool-size N` | `GROUND_TRUTH_CANDIDATE_POOL` | `200` | Số candidate dense retrieval mỗi query đưa vào LLM judge. Lớn hơn = recall tốt hơn, tốn nhiều API call hơn. |
| `--batch-size N` | `QUERY_GENERATION_BATCH_SIZE` | `10` | Số sách gửi cho LLM trong 1 batch khi sinh query. |
| `--queries-per-book N` | `QUERIES_PER_BOOK` | `3` | Số query sinh ra cho mỗi cuốn sách. |

```bash
# Dry run nhanh: pool nhỏ, 1 query mỗi sách, batch nhỏ
python -m src.main build-ground-truth --pool-size 20 --queries-per-book 1 --batch-size 3

# Chỉ override pool size
python -m src.main build-ground-truth --pool-size 50
```

#### Chế độ Append vs Resume

| Flag | Hành vi |
|---|---|
| _(không có flag)_ — **resume** (mặc định) | Load `qrels.json` hiện có, **bỏ qua** các `query_id` đã xử lý → tiếp tục sau khi bị gián đoạn. |
| `--append` | Load `qrels.json` hiện có (giữ toàn bộ dữ liệu cũ), nhưng **không lọc** `done_query_ids` → mọi query trong lần chạy này đều được xử lý và thêm vào file. |

```bash
# Lần 1: chạy thử với cấu hình nhỏ
python -m src.main build-ground-truth --queries-per-book 1 --pool-size 20

# Lần 2: thêm kết quả với cấu hình lớn hơn → APPEND vào qrels.json
python -m src.main build-ground-truth --queries-per-book 2 --pool-size 100 --append
```

> **Tip**: Dùng `--append` để tích luỹ ground truth qua nhiều lần chạy với tham số khác nhau;  
> dùng **resume** (mặc định) để phục hồi sau Ctrl+C mà không sinh query trùng lặp.

---

### Step 3 – Evaluate All Retrievers

Runs all five retrievers against the qrels and produces a benchmark report.

```bash
python -m src.main evaluate
```

**Prerequisites**: Steps 1 & 2 complete  
**Creates**: `data/eval/evaluation_results.json`

---

### Full Pipeline (one command)

```bash
python -m src.main build-indexes && python -m src.main build-ground-truth && python -m src.main evaluate
```

---

## 🌍 Environment Variable Reference

All variables have defaults. Override in `.env`:

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | *(required)* | OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o-mini` | LLM for query gen + judging |
| `TEMPERATURE` | `0.0` | LLM temperature |
| `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | Bi-encoder model |
| `RERANK_MODEL` | `BAAI/bge-reranker-base` | Cross-encoder model |
| `DATASET_PATH` | `data/processed/books_clean.csv` | Preprocessed dataset |
| `MAX_BOOKS_TO_PROCESS` | `500` | Corpus size cap |
| `BOOK_BATCH_SIZE` | `64` | Embedding batch size |
| `QUERIES_PER_BOOK` | `3` | Generated queries per book |
| `QUERY_GENERATION_BATCH_SIZE` | `10` | Books per LLM batch call |
| `DENSE_TOP_K` | `10` | Dense retrieval depth |
| `HYBRID_CANDIDATE_POOL` | `50` | Candidates per sub-retriever (RRF) |
| `RERANK_CANDIDATE_POOL` | `20` | Candidates for cross-encoder |
| `RRF_K` | `60` | Reciprocal Rank Fusion constant |
| `GROUND_TRUTH_CANDIDATE_POOL` | `200` | Dense candidates for GT judging |
| `RELEVANCE_THRESHOLD` | `1` | Min score for qrel inclusion (0/1/2) |
| `EVAL_TOP_K` | `10` | Metric evaluation depth |
| `TFIDF_MAX_FEATURES` | `15000` | TF-IDF vocabulary size |
| `BM25_K1` | `1.5` | BM25 term frequency saturation |
| `BM25_B` | `0.75` | BM25 document length normalisation |

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_metrics.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing
```

All tests use mocks for LLM and vector database calls – **no API keys needed for testing**.

---

## 📊 Expected Output: `evaluation_results.json`

```json
{
  "tfidf": {
    "retriever_name": "tfidf",
    "precision_at_5": 0.2400,
    "precision_at_10": 0.1900,
    "recall_at_5": 0.1800,
    "recall_at_10": 0.2800,
    "mrr": 0.5200,
    "ndcg_at_10": 0.3400,
    "map_score": 0.2900,
    "num_queries": 50,
    "latency_ms": 12.4
  },
  "bm25": { "..." : "..." },
  "dense": { "..." : "..." },
  "hybrid_rrf": { "..." : "..." },
  "rerank": { "..." : "..." },
  "_meta": {
    "eval_top_k": 10,
    "num_qrels": 50,
    "created_at": "2026-06-06T..."
  }
}
```

---

## 🔄 Project Workflow

```
Dataset (CSV)
    │
    ▼
Preprocessing (clean text, deduplicate)
    │
    ▼
build-indexes (TF-IDF + BM25 + ChromaDB)
    │
    ▼
build-ground-truth
    ├── Batch Query Generation (LLM)
    ├── Dense Retrieval (200 candidates per query)
    └── LLM Relevance Judging → qrels.json
    │
    ▼
evaluate
    ├── TF-IDF search × all queries
    ├── BM25 search × all queries
    ├── Dense search × all queries
    ├── Hybrid RRF search × all queries
    └── Reranking search × all queries
    │
    ▼
evaluation_results.json
```

---

## 🧠 Design Decisions

- **No global LLM state**: all chains built via factory functions with injected settings
- **Structured output everywhere**: `llm.with_structured_output(PydanticModel)` — no JSON parsing
- **GT independent of hybrid**: ground truth uses dense-only candidates to avoid evaluation bias  
- **Batch query generation**: N books → 1 API call to minimise cost and latency
- **In-memory judge cache**: avoids re-scoring identical (query, isbn) pairs
- **Pure metric functions**: all metrics are side-effect-free for easy testing
- **Lazy model loading**: encoders and cross-encoders load only when `search()` is first called

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `langchain`, `langchain-openai` | LLM orchestration + structured output |
| `pydantic`, `pydantic-settings` | Schema validation + configuration |
| `scikit-learn` | TF-IDF vectoriser |
| `rank-bm25` | BM25Okapi index |
| `sentence-transformers` | Bi-encoder + cross-encoder models |
| `chromadb` | Vector database for dense embeddings |
| `typer` | CLI framework |
| `tenacity` | Retry with exponential backoff |
| `pandas`, `numpy`, `scipy` | Data manipulation |

---

## 📜 License

MIT License — free to use for academic and research purposes.