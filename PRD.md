# Product Requirements Document
## Semantic Book Recommender System
**Course:** IT4142 — Introduction to Data Science  
**University:** HUST (Hanoi University of Science and Technology)  
**Team size:** 8 members  
**Last updated:** 2026-05-25

---

## 0. Document Purpose

This PRD defines **what** we are building, **why**, and **how** to evaluate success. It serves as the single source of truth for all 8 team members across the ML, Backend, and Frontend tracks.

> **Priority order (must follow strictly):**  
> **Phase 1 → ML Pipeline & Evaluation** (get numbers first)  
> **Phase 2 → Backend API** (serve the models)  
> **Phase 3 → Frontend UI** (consume the API)

---

## 1. Problem Statement

Users who want to discover books often struggle with keyword-based search engines (e.g., "mystery Japan" returns nothing if descriptions use different words). The goal is a system that understands **semantic intent** from natural language queries.

**The core research question:**
> *How much does moving from sparse (keyword-based) retrieval to dense (semantic) retrieval — and hybrid combinations — improve book discovery quality?*

**Example:**
- User types: *"a heartbreaking story about family secrets in rural America"*
- System returns: top-5 relevant books with cover, rating, and emotional tone tag

**The vocabulary mismatch problem (motivation for our approach):**

| Query term | What books actually say |
|---|---|
| "losing their mind slowly" | "psychological deterioration", "mental collapse" |
| "a tearful reunion" | "emotional reconciliation", "bittersweet homecoming" |
| "set in the Far East" | "Tokyo", "Kyoto", "feudal Japan" |

Traditional keyword search scores **0** on these queries. Semantic search handles them naturally.

---

## 2. Scope

### In Scope (MVP — Phase 1–3)
| Feature | Priority | Phase |
|---|---|---|
| Semantic search via natural language query | P0 | ML → BE → FE |
| Emotion-tone filter (joy, fear, sadness…) | P1 | ML → BE → FE |
| **5-model retrieval comparison** (TF-IDF / BM25 / Dense / Hybrid / Reranking) | P0 | ML → FE |
| Book detail view (cover, description, rating) | P1 | FE |
| **Latency vs quality tradeoff visualization** | P1 | ML → FE |

### Out of Scope (explicitly excluded)
- Fiction / Nonfiction classification model (dropped — categories field already provides this)
- User authentication (login / logout / register)
- Personalized recommendation history
- Admin panel
- Mobile app
- Payment / subscription
- Security hardening (rate limiting, auth middleware)

---

## 3. Team Structure & Module Ownership

| Module | Responsible | Members (suggested) |
|---|---|---|
| **M1** Data Collection + EDA + Preprocessing | Data Team | Member 1, 2, 3 |
| **M2a** Sparse Baselines — TF-IDF + BM25 + evaluation framework | ML Team | Member 4 |
| **M2b** Dense Retrieval — BGE-small + ChromaDB | ML Team | Member 5 |
| **M2c** Hybrid Search — Reciprocal Rank Fusion (RRF) | ML Team | Member 6 |
| **M2d** Cross-encoder Reranking + Final Comparison Report | ML Team | Member 4, 5 |
| **M3** Backend API (FastAPI) | BE Team | Member 7 |
| **M4** Frontend (React) | FE Team | Member 8 |

> M3 and M4 can start **after M2a/M2b produce stable model artifacts** (.pkl, .npz, ChromaDB).  
> M2c and M2d run in parallel with M3/M4.

---

## 4. Dataset

### 4.1 Source
| Property | Detail |
|---|---|
| Name | 7K Books with Metadata |
| Source | Kaggle — `dylanjcastillo/7k-books-with-metadata` |
| Origin | Google Books API |
| Raw size | ~7,000 records |
| Clean size | ~5,200 records (after dropping missing `description`) |
| License | Public domain (Kaggle) |

### 4.2 Why this dataset?
1. `description` field is long enough (avg ~150 words) for meaningful NLP
2. `categories` field provides a free proxy label for retrieval evaluation
3. `average_rating` + `ratings_count` enable quality filtering
4. `thumbnail` URL enables book cover display in the UI
5. Widely used in NLP tutorials → easier to find reference implementations

### 4.3 Key Features Used
| Feature | Type | Used for |
|---|---|---|
| `description` | Text | Primary NLP input — embedding + retrieval |
| `categories` | String | Ground truth proxy for retrieval evaluation |
| `title`, `authors` | String | Display in UI |
| `thumbnail` | URL | Book cover image in UI |
| `average_rating` | Float (1–5) | Display + optional ranking weight |
| `published_year` | Int | EDA + optional filter |
| `num_pages` | Int | EDA |

---

## 5. Data Pipeline (M1 Responsibilities)

### Step 1 — Data Collection
- Download via Kaggle API: `kaggle datasets download dylanjcastillo/7k-books-with-metadata`
- Save raw file to `data/raw/books.csv`

### Step 2 — Data Cleaning
| Issue | Action |
|---|---|
| Missing `description` | **Drop row** (description is mandatory for NLP) |
| Missing `thumbnail` | Fill with placeholder image URL |
| Missing `average_rating` | Fill with dataset median |
| Missing `categories` | Fill with `"Unknown"` |
| Duplicate `isbn13` | Keep first occurrence |
| `num_pages` outliers | IQR filter (remove < 10 or > 1500 pages) |
| `published_year` outliers | Keep 1800–2024 only |

### Step 3 — Feature Engineering
```
new features:
- description_length   = len(description.split())
- book_age             = 2024 - published_year
- tag_clean            = categories lowercased + stripped
```

### Step 4 — EDA & Visualization (minimum 5 insights)
Produce the following plots to `reports/figures/`:
1. Distribution of `average_rating` (histogram)
2. Distribution of `description_length` (histogram + box plot)
3. Top 20 categories (bar chart)
4. `published_year` distribution (line chart by decade)
5. Correlation heatmap: `num_pages`, `average_rating`, `ratings_count`, `description_length`
6. Emotion distribution across full corpus (after emotion model runs — bar chart)

### Step 5 — Final Clean Dataset
- Save to `data/processed/books_clean.csv`
- Required columns: `isbn13`, `title`, `authors`, `description`, `categories`, `thumbnail`, `average_rating`, `published_year`, `description_length`

---

## 6. ML Pipeline

### 6.1 Problem Reformulation

```
Input:  Natural language query string (e.g. "a sad story about war and loss")
Output: List of top-K books, each containing:
        {title, authors, description_snippet, cover_url, rating,
         top_emotions, similarity_score}
```

### 6.2 Sub-task A — Retrieval Comparison (5 models)

This is the **core research contribution** of the project. We compare 5 retrieval strategies across 2 axes:

**Axis 1 — Retrieval approach:**
```
Sparse (traditional)  →  Dense (proposed)  →  Hybrid  →  Dense + Rerank
     TF-IDF                 BGE-small           RRF        BGE + cross-encoder
     BM25
```

**Axis 2 — Quality vs speed tradeoff:**
```
Fastest ←────────────────────────────────────────→ Most accurate
TF-IDF    BM25    BGE-small    Hybrid RRF    BGE + Reranking
~5ms      ~10ms   ~50ms        ~60ms         ~200ms
```

---

#### Model 1 — TF-IDF + Cosine Similarity (Sparse Baseline)
```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

vectorizer = TfidfVectorizer(max_features=15000, ngram_range=(1,2),
                              sublinear_tf=True, stop_words='english')
tfidf_matrix = vectorizer.fit_transform(df['description'])

def search_tfidf(query, top_k=10):
    q_vec = vectorizer.transform([query])
    scores = cosine_similarity(q_vec, tfidf_matrix).flatten()
    top_idx = np.argsort(scores)[::-1][:top_k]
    return df.iloc[top_idx]
```

---

#### Model 2 — BM25 (Sparse Baseline)
```python
from rank_bm25 import BM25Okapi

corpus = [desc.lower().split() for desc in df['description']]
bm25 = BM25Okapi(corpus, k1=1.5, b=0.75)

def search_bm25(query, top_k=10):
    scores = bm25.get_scores(query.lower().split())
    top_idx = np.argsort(scores)[::-1][:top_k]
    return df.iloc[top_idx]
```

---

#### Model 3 — Dense Embedding + ChromaDB (Proposed)
```python
from sentence_transformers import SentenceTransformer
import chromadb

model = SentenceTransformer('BAAI/bge-small-en-v1.5')
# BGE prefix for queries (improves retrieval quality)
BGE_PREFIX = 'Represent this sentence for searching relevant passages: '

embeddings = model.encode(df['description'].tolist(), batch_size=64,
                           normalize_embeddings=True, show_progress_bar=True)

client = chromadb.PersistentClient(path="data/chroma_db")
collection = client.get_or_create_collection("books",
    metadata={"hnsw:space": "cosine"})
collection.add(
    documents=df['description'].tolist(),
    embeddings=embeddings.tolist(),
    ids=df['isbn13'].tolist(),
    metadatas=df[['title','authors','thumbnail','average_rating','top_emotions']].to_dict('records')
)

def search_semantic(query, top_k=10, filter_emotions=None):
    q_emb = model.encode([BGE_PREFIX + query], normalize_embeddings=True)
    where = {"$or": [{"top_emotions": {"$contains": e}} for e in filter_emotions]} \
            if filter_emotions else None
    results = collection.query(query_embeddings=q_emb.tolist(),
                               n_results=top_k, where=where)
    return results
```

---

#### Model 4 — Hybrid Search: Reciprocal Rank Fusion (Proposed)

**Why RRF?** Combines the complementary strengths of BM25 (exact keyword match) and dense retrieval (semantic understanding) without requiring manual weight tuning.

```python
def reciprocal_rank_fusion(ranked_lists: list[list], k: int = 60) -> list:
    """
    Merge multiple ranked result lists using RRF.
    k=60 is the standard default (from the original RRF paper).
    
    Args:
        ranked_lists: list of lists, each list is [isbn13, isbn13, ...] sorted by rank
        k: RRF constant (higher k = less penalty for lower ranks)
    Returns:
        Merged ranked list of isbn13
    """
    scores = {}
    for ranked_list in ranked_lists:
        for rank, doc_id in enumerate(ranked_list):
            if doc_id not in scores:
                scores[doc_id] = 0
            scores[doc_id] += 1 / (k + rank + 1)
    
    return sorted(scores, key=scores.get, reverse=True)


def search_hybrid_rrf(query: str, top_k: int = 10) -> pd.DataFrame:
    """
    Hybrid retrieval: BM25 + BGE-small merged with RRF.
    Retrieves top-50 candidates from each model, then fuses.
    """
    CANDIDATE_POOL = 50

    # Get ranked lists from each model
    bm25_results   = search_bm25(query, top_k=CANDIDATE_POOL)
    dense_results  = search_semantic(query, top_k=CANDIDATE_POOL)

    bm25_ids  = bm25_results['isbn13'].tolist()
    dense_ids = [r for r in dense_results['ids'][0]]

    # Fuse
    fused_ids = reciprocal_rank_fusion([bm25_ids, dense_ids])[:top_k]

    # Return book metadata for fused ids
    result = df[df['isbn13'].astype(str).isin(fused_ids)].copy()
    result['rrf_rank'] = result['isbn13'].astype(str).map(
        {isbn: rank for rank, isbn in enumerate(fused_ids)}
    )
    return result.sort_values('rrf_rank').reset_index(drop=True)
```

---

#### Model 5 — Dense + Cross-encoder Reranking (Proposed)

**Why reranking?** Bi-encoders (BGE-small) encode query and document independently → fast but less precise. Cross-encoders read (query, document) jointly → much more accurate but too slow for full corpus. Solution: **2-stage pipeline**.

```
Stage 1 (Recall):  BGE-small → top-20 candidates  (~50ms)
Stage 2 (Precision): Cross-encoder → rerank top-5 (~150ms)
Total:                                              (~200ms)
```

```python
# pip install sentence-transformers
from sentence_transformers import CrossEncoder

cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

def search_with_reranking(query: str, top_k: int = 5,
                           candidate_pool: int = 20) -> pd.DataFrame:
    """
    2-stage retrieval:
    1. BGE-small bi-encoder → top-N candidates (fast)
    2. Cross-encoder → rerank candidates (accurate)
    """
    # Stage 1: dense retrieval for candidate pool
    candidates = search_semantic(query, top_k=candidate_pool)
    candidate_ids   = candidates['ids'][0]
    candidate_metas = candidates['metadatas'][0]
    candidate_docs  = candidates['documents'][0]

    # Stage 2: cross-encoder reranking
    pairs = [(query, doc) for doc in candidate_docs]
    rerank_scores = cross_encoder.predict(pairs)

    # Sort by cross-encoder score
    ranked = sorted(
        zip(candidate_ids, candidate_metas, rerank_scores),
        key=lambda x: x[2], reverse=True
    )[:top_k]

    rows = [{
        'isbn13'         : r[0],
        'title'          : r[1].get('title', ''),
        'authors'        : r[1].get('authors', ''),
        'categories'     : r[1].get('categories', ''),
        'average_rating' : r[1].get('average_rating', 0),
        'rerank_score'   : round(float(r[2]), 4),
    } for r in ranked]

    return pd.DataFrame(rows)
```

---

#### Ground Truth Construction (M2a responsibility)
Since no labeled retrieval dataset exists, use **category-based proxy evaluation**:

1. Create 50 test queries — save to `data/eval/test_queries.json`
2. Format:
```json
[
  {
    "query": "a thriller set in Japan with a detective protagonist",
    "relevant_categories": ["Mystery & Detective", "Thriller", "Fiction"]
  }
]
```
3. A result is **relevant** if its `categories` contains at least one `relevant_categories` entry
4. Compute metrics automatically across all 50 queries

---

#### Evaluation Metrics

| Metric | Formula | Why use it |
|---|---|---|
| **Precision@K** | # relevant in top-K / K | Measures result quality at a given cutoff |
| **MRR** | mean(1 / rank of first relevant result) | Penalizes models that bury the first relevant result |
| **Latency (ms/query)** | wall-clock time per query | Practical deployment consideration |

**MRR formula:**
$$MRR = \frac{1}{|Q|} \sum_{i=1}^{|Q|} \frac{1}{\text{rank}_i}$$

where $\text{rank}_i$ is the position of the first relevant result for query $i$.

---

#### Evaluation Table (fill in after running)
| Model | Type | P@5 | P@10 | MRR | ms/query |
|---|---|---|---|---|---|
| TF-IDF + Cosine | Sparse baseline | ? | ? | ? | ~5 |
| BM25 | Sparse baseline | ? | ? | ? | ~10 |
| BGE-small + ChromaDB | Dense | ? | ? | ? | ~50 |
| **Hybrid RRF** | Dense + Sparse | ? | ? | ? | ~60 |
| **BGE + Reranking** | Dense + Rerank | ? | ? | ? | ~200 |

---

### 6.3 Sub-task B — Emotion Detection (no comparison needed)

Used as a metadata filter, not a standalone model comparison.

```python
from transformers import pipeline

emotion_pipe = pipeline(
    "text-classification",
    model="j-hartmann/emotion-english-distilroberta-base",
    top_k=None,
    device=-1
)

# Run once on full corpus, store results in ChromaDB metadata
# top_emotions = top-2 emotion labels per book
```

**Emotion labels:** joy, sadness, anger, fear, surprise, disgust, neutral

**Deliverable:** Bar chart of emotion distribution across corpus (`reports/figures/emotion_distribution.png`)

---

### 6.4 Artifacts to produce (output of Phase 1)

| Artifact | Path | Used by |
|---|---|---|
| Clean dataset | `data/processed/books_clean.csv` | All |
| TF-IDF vectorizer | `models/tfidf_vectorizer.pkl` | BE |
| TF-IDF matrix | `models/tfidf_matrix.npz` | BE |
| BM25 index | `models/bm25_index.pkl` | BE |
| ChromaDB collection | `data/chroma_db/` | BE |
| 50 test queries | `data/eval/test_queries.json` | Evaluation |
| Evaluation results | `reports/evaluation_final.json` | Report |

---

### 6.5 Key Visualizations for Report & Demo

| Figure | Description | Who makes it |
|---|---|---|
| Vocabulary mismatch demo table | 5–10 queries where TF-IDF/BM25 score=0 but semantic succeeds | M2b |
| Grouped bar chart (P@5, P@10, MRR) | All 5 models side-by-side | M2d |
| Radar chart (P@5 by genre group) | Each axis = genre, each polygon = 1 model | M2d |
| Latency vs P@5 scatter plot | X = ms/query, Y = P@5 → sweet spot visible | M2d |
| Heatmap: model × genre | P@5 per genre per model | M2d |
| UMAP embedding visualization | 2D projection of book embeddings colored by category | M2b |

---

## 7. Backend API (Phase 2)

**Framework:** FastAPI (Python)  
**Entry point:** `backend/main.py`

### 7.1 Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/search` | Main search endpoint |
| `GET` | `/books/{isbn13}` | Single book detail |
| `GET` | `/stats` | Dataset stats for dashboard |

### 7.2 POST /search — Request & Response

**Request body:**
```json
{
  "query": "a heartbreaking story about family secrets",
  "top_k": 10,
  "method": "semantic",
  "filter_emotions": ["sadness", "fear"]
}
```
- `method`: `"tfidf"` | `"bm25"` | `"semantic"` | `"hybrid"` | `"reranking"`
- `filter_emotions`: list of emotion labels | `null`

**Response:**
```json
{
  "results": [
    {
      "isbn13": "9780...",
      "title": "...",
      "authors": "...",
      "description": "...",
      "thumbnail": "https://...",
      "average_rating": 4.2,
      "top_emotions": ["sadness", "fear"],
      "similarity_score": 0.87
    }
  ],
  "method_used": "semantic",
  "total_results": 10,
  "query_time_ms": 120
}
```

### 7.3 CORS
```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware, allow_origins=["*"])
```

### 7.4 Model loading
All models load **once at startup** via FastAPI lifespan. No per-request model loading.

---

## 8. Frontend UI (Phase 3)

**Framework:** React + Vite + TypeScript  
**Styling:** Tailwind CSS + Shadcn UI  
**Data fetching:** TanStack Query (React Query)

### 8.1 Pages & Components

| Page/Component | Description |
|---|---|
| `SearchPage` | Main page — search bar + method selector + emotion filter + results grid |
| `BookCard` | Cover, title, author, rating, emotion badge |
| `BookDetailModal` | Full description, all emotion scores, metadata |
| `FilterPanel` | Emotion multi-select |
| `MethodToggle` | Switch between all 5 retrieval methods |
| `EvaluationDashboard` | Static page — full comparison table + bar chart + radar + scatter |

### 8.2 Key UX flows

**Flow 1 — Search**
```
User types query
  → selects method (default: Semantic)
  → applies emotion filter (optional)
  → clicks Search
  → BookCard grid renders with skeleton loading
  → Click card → BookDetailModal opens
```

**Flow 2 — Method Comparison (demo feature)**
```
User types query → clicks "Compare All Methods"
  → 3 columns: TF-IDF | BM25 | Semantic (Hybrid and Reranking in tabs)
  → Results shown side-by-side
  → Query time shown per method
```

**Flow 3 — Vocabulary Mismatch Demo**
```
Evaluation page → "Demo: Keyword Gap" section
  → Preset paraphrase queries (e.g. "losing their mind slowly")
  → Shows TF-IDF score = 0 vs Semantic score > 0
  → Highlights WHY semantic search is better
```

### 8.3 API integration
```typescript
// hooks/useSearch.ts
const useSearch = (params: SearchParams) =>
  useQuery({
    queryKey: ['search', params],
    queryFn: () => api.post('/search', params).then(r => r.data),
    enabled: !!params.query,
  });
```

---

## 9. Project File Structure

```
semantic-book-recommender/
│
├── data/
│   ├── raw/                    # books.csv (original from Kaggle)
│   ├── processed/              # books_clean.csv, books_with_emotions.csv
│   ├── eval/                   # test_queries.json (50 queries)
│   └── chroma_db/              # ChromaDB persistent storage
│
├── models/
│   ├── tfidf_vectorizer.pkl
│   ├── tfidf_matrix.npz
│   └── bm25_index.pkl
│   # cross-encoder loaded from HuggingFace at runtime (no pkl needed)
│
├── notebooks/
│   ├── 01_data_collection.ipynb
│   ├── 02_eda_visualization.ipynb
│   ├── 03_preprocessing.ipynb
│   ├── 04_retrieval_baseline.ipynb      ← TF-IDF + BM25 + 50 test queries
│   ├── 05_retrieval_proposed.ipynb      ← BGE Embedding + ChromaDB
│   ├── 06_emotion_detection.ipynb       ← DistilRoBERTa, run on full corpus
│   ├── 07_evaluation_comparison.ipynb  ← All 5 models, Precision@K + MRR + charts
│   ├── 08_hybrid_rrf.ipynb              ← Reciprocal Rank Fusion
│   └── 09_reranking.ipynb               ← Cross-encoder reranking
│
├── backend/
│   ├── main.py
│   ├── routers/
│   │   ├── search.py
│   │   └── books.py
│   ├── services/
│   │   └── retrieval.py        # TF-IDF, BM25, Semantic, Hybrid, Reranking logic
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── SearchPage.tsx
│   │   │   └── EvaluationDashboard.tsx
│   │   ├── components/
│   │   │   ├── BookCard.tsx
│   │   │   ├── BookDetailModal.tsx
│   │   │   ├── FilterPanel.tsx
│   │   │   └── MethodToggle.tsx
│   │   ├── hooks/
│   │   │   └── useSearch.ts
│   │   └── lib/
│   │       └── api.ts
│   └── package.json
│
├── reports/
│   ├── figures/
│   └── evaluation_final.json
│
└── README.md
```

---

## 10. Evaluation Summary

### Retrieval — Precision@K + MRR (50 test queries)
| Model | Type | P@5 | P@10 | MRR | ms/query |
|---|---|---|---|---|---|
| TF-IDF + Cosine | Sparse baseline | ? | ? | ? | ~5 |
| BM25 | Sparse baseline | ? | ? | ? | ~10 |
| BGE-small + ChromaDB | Dense | ? | ? | ? | ~50 |
| **Hybrid RRF** | Dense + Sparse | ? | ? | ? | ~60 |
| **BGE + Reranking** | Dense + Rerank | ? | ? | ? | ~200 |

### Expected narrative
- Sparse baselines perform well on **exact keyword queries** but fail on paraphrase/semantic queries
- Dense retrieval improves significantly on **vocabulary mismatch** queries
- Hybrid RRF provides the best **precision/latency tradeoff** (sweet spot)
- Reranking achieves the **highest precision** at the cost of latency (~4× slower than dense alone)

---

## 11. Milestones

| Week | Deliverable | Owner |
|---|---|---|
| Week 1 | `books_clean.csv` + EDA plots + 5 insights | M1 |
| Week 2 | TF-IDF + BM25 baselines running + 50 test queries JSON | M2a |
| Week 2 | Emotion scores computed + stored in ChromaDB metadata | M2b |
| Week 3 | ChromaDB index built + Hybrid RRF implemented | M2b, M2c |
| Week 3 | Cross-encoder reranking + Precision@K + MRR evaluated for all 5 models | M2d |
| Week 3 | FastAPI `/search` endpoint working locally (all 5 methods) | M3 |
| Week 4 | React frontend complete (Search + Comparison + Detail + Eval Dashboard) | M4 |
| Week 4 | Final report + README + demo video | All |

---

## 12. Tech Stack Summary

| Layer | Tool | Version |
|---|---|---|
| Data processing | pandas, numpy | latest |
| ML baselines | scikit-learn, rank_bm25 | latest |
| Bi-encoder model | `BAAI/bge-small-en-v1.5` | HuggingFace |
| Cross-encoder model | `cross-encoder/ms-marco-MiniLM-L-6-v2` | HuggingFace |
| Emotion model | `j-hartmann/emotion-english-distilroberta-base` | HuggingFace |
| Vector database | chromadb | ≥0.5 |
| Visualization | matplotlib, seaborn, plotly | latest |
| Backend | FastAPI + uvicorn | latest |
| Frontend | React + Vite + TypeScript | latest |
| UI components | Tailwind CSS + Shadcn UI | latest |
| Data fetching | TanStack Query (React Query) | v5 |

---

## 13. Research Contribution Summary

> *This section is for the final report / presentation.*

**What we show:**

1. **Quantitative:** Dense retrieval (BGE-small) outperforms sparse baselines (TF-IDF, BM25) by X% on P@5 and Y% on MRR across 50 diverse queries.

2. **Qualitative:** On vocabulary mismatch queries (where user language ≠ book language), sparse methods score near 0 while semantic search returns highly relevant results.

3. **System design:** Hybrid RRF achieves competitive quality with dense retrieval at near-sparse latency, making it the optimal choice for production deployment.

4. **Diminishing returns:** Cross-encoder reranking adds +Z% MRR over dense alone, at the cost of 4× latency — useful for high-stakes queries, overkill for casual browsing.

---

*Document owner: All team members. Update this PRD when scope changes.*
