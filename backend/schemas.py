"""
Pydantic request/response models for the API layer.

These schemas define the contract between the FastAPI backend and the
React frontend. Field names match what the frontend expects.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# =============================================================================
# Constants
# =============================================================================
EMOTIONS = ["joy", "sadness", "anger", "fear", "surprise", "disgust", "neutral"]
VALID_METHODS = ("tfidf", "bm25", "semantic", "hybrid", "reranking")


# =============================================================================
# Search
# =============================================================================
class SearchRequest(BaseModel):
    """POST /search request body."""

    query: str = Field(description="Natural-language search query.")
    top_k: int = Field(default=10, ge=1, le=100, description="Number of results.")
    method: Literal["tfidf", "bm25", "semantic", "hybrid", "reranking"] = Field(
        default="semantic",
        description="Retrieval method to use.",
    )
    filter_emotions: list[str] | None = Field(
        default=None,
        description="Optional emotion filter (e.g. ['fear', 'sadness']).",
    )


class BookResult(BaseModel):
    """A single book in search results."""

    isbn13: str
    title: str
    authors: str
    description: str
    thumbnail: str | None = None
    categories: str
    published_year: int
    average_rating: float = 0.0
    ratings_count: int = 0
    top_emotions: list[str]
    similarity_score: float
    emotion_scores: dict[str, float] | None = None


class SearchResponse(BaseModel):
    """POST /search response."""

    results: list[BookResult]
    method_used: str
    total_results: int
    query_time_ms: float


class CompareRequest(BaseModel):
    """POST /search/compare request body."""

    query: str
    top_k: int = Field(default=10, ge=1, le=100)
    methods: list[str] = Field(
        default=list(VALID_METHODS),
        description="Methods to compare.",
    )


# =============================================================================
# Book Detail
# =============================================================================
class BookDetail(BaseModel):
    """GET /books/{isbn13} response — full book with all fields."""

    isbn13: str
    title: str
    authors: str
    description: str
    thumbnail: str | None = None
    categories: str
    tag_clean: str | None = None
    published_year: int
    num_pages: int | None = None
    description_length: int | None = None
    book_age: int | None = None
    top_emotions: list[str]
    emotion_scores: dict[str, float]


# =============================================================================
# Stats
# =============================================================================
class StatsResponse(BaseModel):
    """GET /stats response."""

    total_books: int
    total_categories: int
    emotion_distribution: dict[str, float]


# =============================================================================
# Evaluation
# =============================================================================
class EvaluationModel(BaseModel):
    """Metrics for a single retrieval method."""

    method: str
    p_at_5: float
    p_at_10: float
    mrr: float
    ndcg_at_10: float | None = None
    map_score: float | None = None
    ms_per_query: float


class GenreScores(BaseModel):
    """Precision@5 scores by genre for each retrieval method."""

    genre: str
    scores: dict[str, float]


class VocabMismatchBook(BaseModel):
    """Simplified book info used in vocabulary mismatch demo."""

    isbn13: str
    title: str
    authors: str
    description: str
    thumbnail: str | None = None
    categories: str
    published_year: int
    top_emotions: list[str]
    emotion_scores: dict[str, float]


class VocabMismatchItem(BaseModel):
    """A single query/result pair demonstrating vocabulary mismatch."""

    query: str
    tfidf_top1: VocabMismatchBook | None = None
    semantic_top1: VocabMismatchBook | None = None


class EvaluationResponse(BaseModel):
    """GET /evaluation response."""

    models: list[EvaluationModel]
    by_genre: list[GenreScores] = []
    vocabulary_mismatch_demo: list[VocabMismatchItem] = []
    meta: dict | None = None
