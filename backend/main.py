"""
Semantic Book Recommender — FastAPI Application

Startup lifecycle:
1. Read books_with_emotions.csv into a pandas DataFrame (in-memory cache)
2. Load/build model artifacts (TF-IDF, BM25, ChromaDB indexes)
3. Instantiate all 5 retrievers from AI/src/retrieval/
4. Serve search, books, stats, and evaluation endpoints

The AI module is imported directly by adding its root to sys.path.
"""

from __future__ import annotations

import logging
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import get_settings

# ---------------------------------------------------------------------------
# Setup: add AI module to Python path so we can import src.retrieval.*
# ---------------------------------------------------------------------------
_BACKEND_DIR = Path(__file__).resolve().parent
_AI_ROOT = (_BACKEND_DIR / ".." / "AI").resolve()

if str(_AI_ROOT) not in sys.path:
    sys.path.insert(0, str(_AI_ROOT))

logger = logging.getLogger("backend")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def load_dataframe(settings) -> pd.DataFrame:
    """Load books_with_emotions.csv into a DataFrame."""
    dataset_path = Path(settings.dataset_path)
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    logger.info("Loading dataset from '%s'…", dataset_path)
    df = pd.read_csv(dataset_path, dtype={"isbn13": str})
    df = df.dropna(subset=["description", "isbn13"])
    df = df.drop_duplicates(subset=["isbn13"], keep="first")
    df["isbn13"] = df["isbn13"].astype(str)

    # Fill optional columns
    for col in ["title", "authors", "categories", "thumbnail", "tag_clean"]:
        if col in df.columns:
            df[col] = df[col].fillna("Unknown")

    logger.info("Dataset loaded: %d books, %d columns", len(df), len(df.columns))
    return df


def ensure_model_artifacts(df: pd.DataFrame, settings) -> None:
    """Build model artifacts if they don't exist on disk."""
    from src.utils.text_utils import clean_text  # noqa: PLC0415

    tfidf_exists = Path(settings.tfidf_model_path).exists()
    bm25_exists = Path(settings.bm25_index_path).exists()
    chroma_exists = Path(settings.chroma_path).exists()

    if tfidf_exists and bm25_exists and chroma_exists:
        logger.info("All model artifacts found on disk ✓")
        return

    logger.info("Model artifacts missing — building now (this may take 5-10 minutes)…")

    # Prepare corpus (same cleaning as AI pipeline)
    df_build = df.copy()
    df_build["description"] = df_build["description"].apply(lambda t: clean_text(str(t)))
    df_build = df_build[df_build["description"].str.split().str.len() >= 10].reset_index(drop=True)
    logger.info("Corpus for indexing: %d books (after filtering short descriptions)", len(df_build))

    if not tfidf_exists:
        from src.retrieval.tfidf_retriever import TFIDFRetriever  # noqa: PLC0415
        logger.info("Building TF-IDF index…")
        TFIDFRetriever.build(
            df=df_build,
            model_path=Path(settings.tfidf_model_path),
            matrix_path=Path(settings.tfidf_matrix_path),
            max_features=settings.tfidf_max_features,
            min_df=settings.tfidf_min_df,
        )
        logger.info("TF-IDF index built ✓")

    if not bm25_exists:
        from src.retrieval.bm25_retriever import BM25Retriever  # noqa: PLC0415
        logger.info("Building BM25 index…")
        BM25Retriever.build(
            df=df_build,
            index_path=Path(settings.bm25_index_path),
            k1=settings.bm25_k1,
            b=settings.bm25_b,
        )
        logger.info("BM25 index built ✓")

    if not chroma_exists:
        from src.retrieval.dense_retriever import DenseRetriever  # noqa: PLC0415
        logger.info("Building ChromaDB dense index (this is the slowest step)…")
        DenseRetriever.build(
            df=df_build,
            chroma_path=Path(settings.chroma_path),
            embedding_model=settings.embedding_model,
            collection_name=settings.chroma_collection_name,
            batch_size=64,
        )
        logger.info("ChromaDB index built ✓")

    logger.info("All model artifacts built successfully ✓")


def load_retrievers(df: pd.DataFrame, settings) -> dict:
    """Instantiate all 5 retrievers using pre-built model artifacts."""
    from src.retrieval.bm25_retriever import BM25Retriever  # noqa: PLC0415
    from src.retrieval.dense_retriever import DenseRetriever  # noqa: PLC0415
    from src.retrieval.hybrid_rrf_retriever import HybridRRFRetriever  # noqa: PLC0415
    from src.retrieval.rerank_retriever import RerankRetriever  # noqa: PLC0415
    from src.retrieval.tfidf_retriever import TFIDFRetriever  # noqa: PLC0415
    from src.utils.text_utils import clean_text  # noqa: PLC0415

    # Prepare the same cleaned DataFrame the indexes were built with
    df_search = df.copy()
    df_search["description"] = df_search["description"].apply(lambda t: clean_text(str(t)))
    df_search = df_search[df_search["description"].str.split().str.len() >= 10].reset_index(drop=True)

    logger.info("Loading TF-IDF retriever…")
    tfidf = TFIDFRetriever.load(
        model_path=Path(settings.tfidf_model_path),
        matrix_path=Path(settings.tfidf_matrix_path),
        df=df_search,
    )

    logger.info("Loading BM25 retriever…")
    bm25 = BM25Retriever.load(
        index_path=Path(settings.bm25_index_path),
        df=df_search,
    )

    logger.info("Connecting Dense (ChromaDB) retriever…")
    dense = DenseRetriever.load(
        chroma_path=Path(settings.chroma_path),
        embedding_model=settings.embedding_model,
        collection_name=settings.chroma_collection_name,
    )

    logger.info("Configuring Hybrid RRF retriever…")
    hybrid = HybridRRFRetriever(
        bm25_retriever=bm25,
        dense_retriever=dense,
        candidate_pool=settings.hybrid_candidate_pool,
        rrf_k=settings.rrf_k,
    )

    logger.info("Configuring Reranking retriever…")
    rerank = RerankRetriever(
        dense_retriever=dense,
        rerank_model=settings.rerank_model,
        candidate_pool=settings.rerank_candidate_pool,
    )

    # Map method names to match what the frontend sends
    retrievers = {
        "tfidf": tfidf,
        "bm25": bm25,
        "semantic": dense,      # frontend calls it "semantic"
        "hybrid": hybrid,
        "reranking": rerank,    # frontend calls it "reranking"
    }

    logger.info("All 5 retrievers loaded ✓")
    return retrievers


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load data and models on startup, clean up on shutdown."""
    settings = get_settings()
    t0 = time.perf_counter()

    # 1. Load DataFrame
    df = load_dataframe(settings)
    app.state.df = df
    app.state.settings = settings

    # 2. Ensure model artifacts exist (build if missing)
    ensure_model_artifacts(df, settings)

    # 3. Load all retrievers
    app.state.retrievers = load_retrievers(df, settings)

    elapsed = time.perf_counter() - t0
    logger.info("Backend startup complete in %.1fs — serving %d books", elapsed, len(df))

    yield

    # Shutdown cleanup (nothing needed for read-only system)
    logger.info("Backend shutting down.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Semantic Book Recommender API",
    description="Search API serving 5 retrieval methods over 11,606 books.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request timing middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    t0 = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.1f}"
    return response


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
from routers import search, books, stats, evaluation  # noqa: E402

app.include_router(search.router, tags=["Search"])
app.include_router(books.router, tags=["Books"])
app.include_router(stats.router, tags=["Stats"])
app.include_router(evaluation.router, tags=["Evaluation"])


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["System"])
async def health_check(request: Request):
    """Quick health check endpoint."""
    df = request.app.state.df
    retrievers = request.app.state.retrievers
    return {
        "status": "ok",
        "total_books": len(df),
        "retrievers_loaded": list(retrievers.keys()),
    }
