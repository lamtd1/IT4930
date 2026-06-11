"""
Build model artifacts for the backend.

This script builds TF-IDF, BM25, and ChromaDB indexes using the
AI module's retriever classes. Run this once before starting the
backend server for the first time.

Usage:
    cd backend
    python scripts/init_models.py

The backend's main.py will also auto-build if artifacts are missing,
but running this script separately lets you monitor the build process.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Add project paths
_SCRIPT_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _SCRIPT_DIR.parent
_AI_ROOT = (_BACKEND_DIR / ".." / "AI").resolve()

sys.path.insert(0, str(_BACKEND_DIR))
sys.path.insert(0, str(_AI_ROOT))

import pandas as pd

from config import get_settings
from src.utils.text_utils import clean_text


def main():
    settings = get_settings()
    print("=" * 60)
    print("BUILD MODEL ARTIFACTS")
    print("=" * 60)

    # 1. Load dataset
    dataset_path = Path(settings.dataset_path)
    print(f"\n1. Loading dataset from '{dataset_path}'…")
    df = pd.read_csv(dataset_path, dtype={"isbn13": str})
    df = df.dropna(subset=["description", "isbn13"])
    df = df.drop_duplicates(subset=["isbn13"], keep="first")
    df["isbn13"] = df["isbn13"].astype(str)

    for col in ["title", "authors", "categories", "thumbnail"]:
        if col in df.columns:
            df[col] = df[col].fillna("Unknown")

    print(f"   Loaded {len(df)} books")

    # 2. Clean text
    print("\n2. Cleaning description text…")
    df["description"] = df["description"].apply(lambda t: clean_text(str(t)))
    df = df[df["description"].str.split().str.len() >= 10].reset_index(drop=True)
    print(f"   Corpus after filtering: {len(df)} books")

    # 3. Build TF-IDF
    tfidf_path = Path(settings.tfidf_model_path)
    if tfidf_path.exists():
        print(f"\n3. TF-IDF index already exists at '{tfidf_path}' — skipping")
    else:
        from src.retrieval.tfidf_retriever import TFIDFRetriever
        print("\n3. Building TF-IDF index…")
        t0 = time.perf_counter()
        TFIDFRetriever.build(
            df=df,
            model_path=tfidf_path,
            matrix_path=Path(settings.tfidf_matrix_path),
            max_features=settings.tfidf_max_features,
            min_df=settings.tfidf_min_df,
        )
        print(f"   TF-IDF built in {time.perf_counter() - t0:.1f}s ✓")

    # 4. Build BM25
    bm25_path = Path(settings.bm25_index_path)
    if bm25_path.exists():
        print(f"\n4. BM25 index already exists at '{bm25_path}' — skipping")
    else:
        from src.retrieval.bm25_retriever import BM25Retriever
        print("\n4. Building BM25 index…")
        t0 = time.perf_counter()
        BM25Retriever.build(
            df=df,
            index_path=bm25_path,
            k1=settings.bm25_k1,
            b=settings.bm25_b,
        )
        print(f"   BM25 built in {time.perf_counter() - t0:.1f}s ✓")

    # 5. Build ChromaDB
    chroma_path = Path(settings.chroma_path)
    if chroma_path.exists():
        print(f"\n5. ChromaDB already exists at '{chroma_path}' — skipping")
    else:
        from src.retrieval.dense_retriever import DenseRetriever
        print("\n5. Building ChromaDB dense index (this may take several minutes)…")
        t0 = time.perf_counter()
        DenseRetriever.build(
            df=df,
            chroma_path=chroma_path,
            embedding_model=settings.embedding_model,
            collection_name=settings.chroma_collection_name,
            batch_size=64,
        )
        print(f"   ChromaDB built in {time.perf_counter() - t0:.1f}s ✓")

    print("\n" + "=" * 60)
    print("ALL ARTIFACTS READY")
    print(f"  TF-IDF:   {settings.tfidf_model_path}")
    print(f"  BM25:     {settings.bm25_index_path}")
    print(f"  ChromaDB: {settings.chroma_path}")
    print("=" * 60)
    print("\nYou can now start the backend:")
    print("  uvicorn main:app --reload --port 8000")


if __name__ == "__main__":
    main()
