"""
Backend configuration using Pydantic Settings.

All values have defaults and can be overridden via .env file or
environment variables.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Backend configuration populated from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # CORS
    # -------------------------------------------------------------------------
    cors_origins: list[str] = Field(
        default=["http://localhost:5173"],
        description="Allowed CORS origins (frontend URL).",
    )

    # -------------------------------------------------------------------------
    # Data Paths (relative to backend/)
    # -------------------------------------------------------------------------
    dataset_path: Path = Field(
        default=Path("../AI/data/processed/books_with_emotions.csv"),
        description="Path to the processed books CSV with emotion scores.",
    )
    chroma_path: Path = Field(
        default=Path("../AI/data/chroma_db"),
        description="Directory where ChromaDB persists its data.",
    )
    eval_final_json: Path = Field(
        default=Path("../AI/reports/evaluation_final.json"),
        description="Path to the curated evaluation results JSON.",
    )
    eval_results_json: Path = Field(
        default=Path("../AI/data/eval/evaluation_results.json"),
        description="Path to the raw evaluation results JSON.",
    )

    # -------------------------------------------------------------------------
    # Model Artifact Paths
    # -------------------------------------------------------------------------
    bm25_index_path: Path = Field(
        default=Path("../AI/models/bm25.pkl"),
        description="Path to the serialised BM25 index pickle.",
    )
    tfidf_model_path: Path = Field(
        default=Path("../AI/models/tfidf.pkl"),
        description="Path to the serialised TF-IDF vectorizer pickle.",
    )
    tfidf_matrix_path: Path = Field(
        default=Path("../AI/models/tfidf_matrix.npz"),
        description="Path to the serialised TF-IDF sparse matrix.",
    )

    # -------------------------------------------------------------------------
    # AI Model Configuration
    # -------------------------------------------------------------------------
    embedding_model: str = Field(
        default="BAAI/bge-small-en-v1.5",
        description="SentenceTransformer model for dense retrieval.",
    )
    rerank_model: str = Field(
        default="BAAI/bge-reranker-base",
        description="CrossEncoder model for reranking candidates.",
    )
    chroma_collection_name: str = Field(
        default="books",
        description="ChromaDB collection name for dense embeddings.",
    )
    max_books_to_process: int = Field(
        default=15000,
        gt=0,
        description="Maximum books to load (set high to use full dataset).",
    )

    # -------------------------------------------------------------------------
    # Retrieval Hyperparameters
    # -------------------------------------------------------------------------
    hybrid_candidate_pool: int = Field(default=50)
    rerank_candidate_pool: int = Field(default=20)
    rrf_k: int = Field(default=60)
    tfidf_max_features: int = Field(default=15000)
    tfidf_min_df: int = Field(default=2)
    bm25_k1: float = Field(default=1.5)
    bm25_b: float = Field(default=0.75)

    # -------------------------------------------------------------------------
    # Validators
    # -------------------------------------------------------------------------
    @field_validator(
        "dataset_path", "chroma_path", "eval_final_json", "eval_results_json",
        "bm25_index_path", "tfidf_model_path", "tfidf_matrix_path",
        mode="before",
    )
    @classmethod
    def coerce_path(cls, v: object) -> Path:
        """Accept strings and convert to Path objects."""
        return Path(str(v))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings singleton."""
    return Settings()
