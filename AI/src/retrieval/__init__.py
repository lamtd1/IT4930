"""
Retrieval package – exports all retriever implementations.

Imports are done lazily via ``__getattr__`` to avoid loading heavy
dependencies (scipy, scikit-learn, rank-bm25, sentence-transformers)
at Python collection time. Only the requested class is imported.
"""

from __future__ import annotations

__all__ = [
    "BaseRetriever",
    "TFIDFRetriever",
    "BM25Retriever",
    "DenseRetriever",
    "HybridRRFRetriever",
    "RerankRetriever",
]

# Always import the abstract base (zero heavy deps)
from src.retrieval.base import BaseRetriever  # noqa: E402


def __getattr__(name: str):
    if name == "TFIDFRetriever":
        from src.retrieval.tfidf_retriever import TFIDFRetriever  # noqa: PLC0415
        return TFIDFRetriever
    if name == "BM25Retriever":
        from src.retrieval.bm25_retriever import BM25Retriever  # noqa: PLC0415
        return BM25Retriever
    if name == "DenseRetriever":
        from src.retrieval.dense_retriever import DenseRetriever  # noqa: PLC0415
        return DenseRetriever
    if name == "HybridRRFRetriever":
        from src.retrieval.hybrid_rrf_retriever import HybridRRFRetriever  # noqa: PLC0415
        return HybridRRFRetriever
    if name == "RerankRetriever":
        from src.retrieval.rerank_retriever import RerankRetriever  # noqa: PLC0415
        return RerankRetriever
    raise AttributeError(f"module 'src.retrieval' has no attribute {name!r}")
