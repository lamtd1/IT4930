"""
Shared pytest fixtures for book retrieval benchmark tests.

Provides:
- ``mock_settings``: minimal Settings object with safe defaults
- ``sample_books``: small list of BookInfo objects for testing
- ``sample_qrels``: small list of QrelItem objects
- ``sample_df``: tiny pandas DataFrame for retriever tests
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

# Ensure src is importable from tests directory
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config.settings import Settings
from src.schemas.benchmark import QrelItem
from src.schemas.query import BookInfo
from src.schemas.retrieval import RetrievalResult


@pytest.fixture
def mock_settings(tmp_path: Path) -> Settings:
    """
    Return a Settings instance pointing to a temp directory.
    No actual .env is required.
    """
    return Settings(
        openai_api_key="test-key",
        openai_model="gpt-4o-mini",
        temperature=0.0,
        embedding_model="BAAI/bge-small-en-v1.5",
        rerank_model="BAAI/bge-reranker-base",
        dataset_path=tmp_path / "books.csv",
        chroma_path=tmp_path / "chroma",
        eval_output_path=tmp_path / "eval",
        bm25_index_path=tmp_path / "models" / "bm25.pkl",
        tfidf_model_path=tmp_path / "models" / "tfidf.pkl",
        tfidf_matrix_path=tmp_path / "models" / "tfidf_matrix.npz",
        log_dir=tmp_path / "logs",
        max_books_to_process=10,
        book_batch_size=4,
        queries_per_book=2,
        query_generation_batch_size=3,
        dense_top_k=5,
        hybrid_candidate_pool=5,
        rerank_candidate_pool=5,
        rrf_k=60,
        ground_truth_candidate_pool=5,
        relevance_threshold=1,
        eval_top_k=5,
        tfidf_max_features=1000,
        tfidf_min_df=1,
        bm25_k1=1.5,
        bm25_b=0.75,
    )


@pytest.fixture
def sample_books() -> list[BookInfo]:
    """Three minimal BookInfo objects for LLM chain tests."""
    return [
        BookInfo(
            isbn13="9780000000001",
            title="The Dark Forest",
            description=(
                "A sci-fi epic about humanity's response to an alien threat. "
                "The Wallfacer project attempts to deceive the invaders using secret plans."
            ),
            categories="Science Fiction",
        ),
        BookInfo(
            isbn13="9780000000002",
            title="The Name of the Wind",
            description=(
                "The tale of Kvothe, a legendary wizard and musician, "
                "told in his own words from a remote inn."
            ),
            categories="Fantasy",
        ),
        BookInfo(
            isbn13="9780000000003",
            title="Thinking, Fast and Slow",
            description=(
                "Nobel laureate Daniel Kahneman reveals the two systems that drive the way we think. "
                "System 1 is fast, intuitive; System 2 is slower and more deliberate."
            ),
            categories="Psychology, Self-Help",
        ),
    ]


@pytest.fixture
def sample_qrels() -> list[QrelItem]:
    """Small qrels dataset for evaluator tests."""
    return [
        QrelItem(
            query_id="q_9780000000001_0",
            query="alien invasion science fiction",
            source_isbn="9780000000001",
            relevant_isbns=["9780000000001", "9780000000004"],
            judge_model="gpt-4o-mini",
            generation_model="gpt-4o-mini",
        ),
        QrelItem(
            query_id="q_9780000000002_0",
            query="fantasy wizard musician coming of age",
            source_isbn="9780000000002",
            relevant_isbns=["9780000000002"],
            judge_model="gpt-4o-mini",
            generation_model="gpt-4o-mini",
        ),
        QrelItem(
            query_id="q_9780000000003_0",
            query="psychology cognitive biases decision making",
            source_isbn="9780000000003",
            relevant_isbns=["9780000000003"],
            judge_model="gpt-4o-mini",
            generation_model="gpt-4o-mini",
        ),
    ]


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """Minimal DataFrame for retriever unit tests."""
    return pd.DataFrame(
        {
            "isbn13": ["9780000000001", "9780000000002", "9780000000003", "9780000000004"],
            "title": ["The Dark Forest", "The Name of the Wind", "Thinking Fast and Slow", "Ender's Game"],
            "description": [
                "A sci-fi epic about humanity response to an alien threat and the Wallfacer project",
                "The tale of a legendary wizard and musician told in his own words",
                "Nobel laureate reveals two systems that drive the way we think fast and slow",
                "Young military genius trains to fight alien invaders in a space battle school",
            ],
            "categories": ["Science Fiction", "Fantasy", "Psychology", "Science Fiction"],
            "authors": ["Liu Cixin", "Patrick Rothfuss", "Daniel Kahneman", "Orson Scott Card"],
            "average_rating": [4.5, 4.6, 4.2, 4.7],
            "published_year": [2008, 2007, 2011, 1985],
            "thumbnail": ["", "", "", ""],
        }
    )


@pytest.fixture
def mock_retrieval_results() -> list[RetrievalResult]:
    """Ordered retrieval results for metric tests."""
    return [
        RetrievalResult(isbn13="9780000000001", score=0.95, rank=1),
        RetrievalResult(isbn13="9780000000004", score=0.80, rank=2),
        RetrievalResult(isbn13="9780000000002", score=0.60, rank=3),
        RetrievalResult(isbn13="9780000000099", score=0.40, rank=4),
        RetrievalResult(isbn13="9780000000003", score=0.30, rank=5),
    ]
