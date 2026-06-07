"""Schemas package for book retrieval benchmark."""

from src.schemas.query import BookInfo, BookQueries, BatchQueryResponse
from src.schemas.relevance import RelevanceScore, BookRelevance, BatchRelevanceResponse
from src.schemas.benchmark import QuerySet, QrelItem, BenchmarkResult, EvalSummary
from src.schemas.retrieval import RetrievalResult

__all__ = [
    "BookInfo",
    "BookQueries",
    "BatchQueryResponse",
    "RelevanceScore",
    "BookRelevance",
    "BatchRelevanceResponse",
    "QuerySet",
    "QrelItem",
    "BenchmarkResult",
    "EvalSummary",
    "RetrievalResult",
]
