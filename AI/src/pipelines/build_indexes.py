"""
Pipeline: Build Retrieval Indexes

Reads the preprocessed books dataset, applies ``MAX_BOOKS_TO_PROCESS`` cap,
and builds / persists three indexes:
  1. TF-IDF vectorizer + sparse matrix
  2. BM25 index
  3. Dense embeddings in ChromaDB

Run as a module:
    python -m src.pipelines.build_indexes

Or via the CLI:
    python -m src.main build-indexes
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

# Ensure project root is on sys.path when run as __main__
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.config.settings import get_settings
from src.retrieval.bm25_retriever import BM25Retriever
from src.retrieval.dense_retriever import DenseRetriever
from src.retrieval.tfidf_retriever import TFIDFRetriever
from src.utils.logging_config import setup_logging
from src.utils.text_utils import clean_text

logger = logging.getLogger(__name__)


def run(settings=None) -> None:
    """
    Execute the index-building pipeline.

    Args:
        settings: Optional pre-constructed ``Settings`` object.
                  If None, ``get_settings()`` is called automatically.
    """
    if settings is None:
        settings = get_settings()

    setup_logging(log_dir=settings.log_dir)
    logger.info("=" * 60)
    logger.info("BUILD INDEXES PIPELINE")
    logger.info("=" * 60)

    # ------------------------------------------------------------------
    # 1. Load dataset
    # ------------------------------------------------------------------
    dataset_path = Path(settings.dataset_path)
    if not dataset_path.exists():
        logger.error("Dataset not found at '%s'. Run preprocessing first.", dataset_path)
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    logger.info("Loading dataset from '%s'…", dataset_path)
    df = pd.read_csv(dataset_path, dtype={"isbn13": str})
    df = df.dropna(subset=["description", "isbn13"])
    df = df.drop_duplicates(subset=["isbn13"], keep="first")

    # Apply corpus size cap
    max_books = settings.max_books_to_process
    if len(df) > max_books:
        logger.info(
            "Capping corpus: %d → %d books (MAX_BOOKS_TO_PROCESS=%d)",
            len(df),
            max_books,
            max_books,
        )
        df = df.head(max_books).copy()

    # Clean text
    logger.info("Cleaning description text for %d books…", len(df))
    df["description"] = df["description"].apply(lambda t: clean_text(str(t)))
    df = df[df["description"].str.split().str.len() >= 10].reset_index(drop=True)
    df["isbn13"] = df["isbn13"].astype(str)

    # Fill optional columns
    for col in ["title", "authors", "categories", "thumbnail"]:
        if col in df.columns:
            df[col] = df[col].fillna("Unknown")

    logger.info("Final corpus size: %d books", len(df))

    # ------------------------------------------------------------------
    # 2. Build TF-IDF index
    # ------------------------------------------------------------------
    logger.info("Building TF-IDF index…")
    TFIDFRetriever.build(
        df=df,
        model_path=Path(settings.tfidf_model_path),
        matrix_path=Path(settings.tfidf_matrix_path),
        max_features=settings.tfidf_max_features,
        min_df=settings.tfidf_min_df,
    )
    logger.info("TF-IDF index complete ✓")

    # ------------------------------------------------------------------
    # 3. Build BM25 index
    # ------------------------------------------------------------------
    logger.info("Building BM25 index…")
    BM25Retriever.build(
        df=df,
        index_path=Path(settings.bm25_index_path),
        k1=settings.bm25_k1,
        b=settings.bm25_b,
    )
    logger.info("BM25 index complete ✓")

    # ------------------------------------------------------------------
    # 4. Build Dense (ChromaDB) index
    # ------------------------------------------------------------------
    logger.info("Building Dense (ChromaDB) index with model '%s'…", settings.embedding_model)
    DenseRetriever.build(
        df=df,
        chroma_path=Path(settings.chroma_path),
        embedding_model=settings.embedding_model,
        collection_name=settings.chroma_collection_name,
        batch_size=settings.book_batch_size,
    )
    logger.info("Dense index complete ✓")

    logger.info("=" * 60)
    logger.info("ALL INDEXES BUILT SUCCESSFULLY")
    logger.info("  TF-IDF model: %s", settings.tfidf_model_path)
    logger.info("  TF-IDF matrix: %s", settings.tfidf_matrix_path)
    logger.info("  BM25 index: %s", settings.bm25_index_path)
    logger.info("  ChromaDB: %s (collection: %s)", settings.chroma_path, settings.chroma_collection_name)
    logger.info("=" * 60)


if __name__ == "__main__":
    run()
