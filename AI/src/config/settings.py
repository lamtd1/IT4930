"""
Settings module for the Book Retrieval Benchmark.

All configuration is read from environment variables (or a .env file).
No values are hardcoded here – every parameter has a documented default
that can be overridden at runtime.

Usage:
    from src.config.settings import get_settings
    settings = get_settings()
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central settings object populated from environment variables / .env file.

    All numeric and string values are fully configurable so the benchmark
    can be run on a small sample (for cost/time testing) or the full corpus.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # OpenAI / LLM
    # -------------------------------------------------------------------------
    openai_api_key: str = Field(
        default="",
        description="OpenAI API key. Required for query generation and relevance judging.",
    )
    openai_model: str = Field(
        default="gpt-4o-mini",
        description="OpenAI chat model identifier used for LLM chains.",
    )
    temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="LLM sampling temperature. 0 = deterministic.",
    )

    # -------------------------------------------------------------------------
    # Embedding / Reranking Models
    # -------------------------------------------------------------------------
    embedding_model: str = Field(
        default="BAAI/bge-small-en-v1.5",
        description="SentenceTransformer model for dense retrieval.",
    )
    rerank_model: str = Field(
        default="BAAI/bge-reranker-base",
        description="CrossEncoder model for reranking candidates.",
    )

    # -------------------------------------------------------------------------
    # File Paths
    # -------------------------------------------------------------------------
    dataset_path: Path = Field(
        default=Path("data/processed/books_clean.csv"),
        description="Path to the preprocessed books CSV file.",
    )
    chroma_path: Path = Field(
        default=Path("data/chroma_db"),
        description="Directory where ChromaDB persists its data.",
    )
    eval_output_path: Path = Field(
        default=Path("data/eval"),
        description="Directory for evaluation outputs (qrels, results).",
    )
    bm25_index_path: Path = Field(
        default=Path("models/bm25.pkl"),
        description="Path to the serialised BM25 index pickle.",
    )
    tfidf_model_path: Path = Field(
        default=Path("models/tfidf.pkl"),
        description="Path to the serialised TF-IDF vectorizer pickle.",
    )
    tfidf_matrix_path: Path = Field(
        default=Path("models/tfidf_matrix.npz"),
        description="Path to the serialised TF-IDF sparse matrix (.npz).",
    )
    log_dir: Path = Field(
        default=Path("logs"),
        description="Directory where log files are written.",
    )

    # -------------------------------------------------------------------------
    # Corpus / Processing Limits
    # -------------------------------------------------------------------------
    max_books_to_process: Annotated[int, Field(gt=0)] = Field(
        default=500,
        description=(
            "Maximum number of books loaded from the dataset. "
            "Reduce for quick testing, increase for full benchmark."
        ),
    )
    book_batch_size: Annotated[int, Field(gt=0)] = Field(
        default=64,
        description="Batch size used when encoding embeddings.",
    )

    # -------------------------------------------------------------------------
    # Query Generation
    # -------------------------------------------------------------------------
    queries_per_book: Annotated[int, Field(gt=0)] = Field(
        default=3,
        description="Number of search queries generated per book.",
    )
    query_generation_batch_size: Annotated[int, Field(gt=0)] = Field(
        default=10,
        description="Number of books sent to the LLM in a single batch call.",
    )

    # -------------------------------------------------------------------------
    # Retrieval Parameters
    # -------------------------------------------------------------------------
    dense_top_k: Annotated[int, Field(gt=0)] = Field(
        default=10,
        description="Number of results returned by the dense retriever.",
    )
    hybrid_candidate_pool: Annotated[int, Field(gt=0)] = Field(
        default=50,
        description="Candidate pool size for each sub-retriever before RRF fusion.",
    )
    rerank_candidate_pool: Annotated[int, Field(gt=0)] = Field(
        default=20,
        description="Number of dense candidates passed to the cross-encoder.",
    )
    rrf_k: Annotated[int, Field(gt=0)] = Field(
        default=60,
        description="RRF constant k. Higher values reduce the impact of top ranks.",
    )
    chroma_collection_name: str = Field(
        default="books",
        description="ChromaDB collection name for dense embeddings.",
    )

    # -------------------------------------------------------------------------
    # Ground Truth Generation
    # -------------------------------------------------------------------------
    ground_truth_candidate_pool: Annotated[int, Field(gt=0)] = Field(
        default=200,
        description=(
            "Number of dense candidates retrieved per query for LLM judging. "
            "Larger pool improves recall at the cost of more API calls."
        ),
    )

    # -------------------------------------------------------------------------
    # Relevance Judging
    # -------------------------------------------------------------------------
    relevance_threshold: Annotated[int, Field(ge=0, le=2)] = Field(
        default=1,
        description="Minimum relevance score (0/1/2) for a book to appear in qrels.",
    )
    judge_parallel_workers: Annotated[int, Field(gt=0)] = Field(
        default=5,
        description=(
            "Number of concurrent threads for LLM relevance judging per query. "
            "Higher = faster but may hit API rate limits. "
            "Recommended: 5 for free tier, 10-20 for paid tier."
        ),
    )

    # -------------------------------------------------------------------------
    # Evaluation
    # -------------------------------------------------------------------------
    eval_top_k: Annotated[int, Field(gt=0)] = Field(
        default=10,
        description="Depth at which evaluation metrics (P@K, NDCG@K, etc.) are computed.",
    )

    # -------------------------------------------------------------------------
    # TF-IDF Hyperparameters
    # -------------------------------------------------------------------------
    tfidf_max_features: Annotated[int, Field(gt=0)] = Field(
        default=15000,
        description="Maximum vocabulary size for TF-IDF vectorizer.",
    )
    tfidf_min_df: Annotated[int, Field(gt=0)] = Field(
        default=2,
        description="Minimum document frequency for TF-IDF terms.",
    )

    # -------------------------------------------------------------------------
    # BM25 Hyperparameters
    # -------------------------------------------------------------------------
    bm25_k1: float = Field(
        default=1.5,
        gt=0.0,
        description="BM25 k1 parameter (term frequency saturation).",
    )
    bm25_b: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="BM25 b parameter (document length normalization).",
    )

    # -------------------------------------------------------------------------
    # Validators
    # -------------------------------------------------------------------------
    @field_validator("dataset_path", "chroma_path", "eval_output_path",
                     "bm25_index_path", "tfidf_model_path", "tfidf_matrix_path",
                     "log_dir", mode="before")
    @classmethod
    def coerce_path(cls, v: object) -> Path:
        """Accept strings and convert to Path objects."""
        return Path(str(v))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a cached Settings singleton.

    Uses ``@lru_cache`` so the .env file is parsed only once per process.
    In tests, call ``get_settings.cache_clear()`` after monkeypatching env vars.
    """
    return Settings()
