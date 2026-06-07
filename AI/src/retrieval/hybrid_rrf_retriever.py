"""
Hybrid Retriever using Reciprocal Rank Fusion (RRF).

Combines BM25 (sparse lexical) and Dense (semantic) retrieval results
using the RRF algorithm.  No single retriever dominates – rank positions
from both are merged into a unified relevance score.

Reference:
    Cormack, G. V., Clarke, C. L. A., & Buettcher, S. (2009).
    Reciprocal rank fusion outperforms condorcet and individual rank learning methods.
    SIGIR 2009.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from src.retrieval.base import BaseRetriever
from src.schemas.retrieval import RetrievalResult

if TYPE_CHECKING:
    from src.retrieval.bm25_retriever import BM25Retriever
    from src.retrieval.dense_retriever import DenseRetriever

logger = logging.getLogger(__name__)


class HybridRRFRetriever(BaseRetriever):
    """
    Hybrid retriever that fuses BM25 and Dense results with RRF.

    Args:
        bm25_retriever:   Initialised BM25Retriever.
        dense_retriever:  Initialised DenseRetriever.
        candidate_pool:   Number of candidates retrieved from each sub-retriever
                          before fusion.  Should be larger than ``top_k``.
        rrf_k:            RRF constant k (default 60).  Controls the impact of
                          rank position: higher k → more uniform weighting.
        bm25_weight:      Weight multiplier applied to BM25 RRF scores (default 1.0).
        dense_weight:     Weight multiplier applied to Dense RRF scores (default 1.0).
    """

    def __init__(
        self,
        bm25_retriever: BM25Retriever,
        dense_retriever: DenseRetriever,
        candidate_pool: int = 50,
        rrf_k: int = 60,
        bm25_weight: float = 1.0,
        dense_weight: float = 1.0,
    ) -> None:
        self._bm25 = bm25_retriever
        self._dense = dense_retriever
        self._candidate_pool = candidate_pool
        self._rrf_k = rrf_k
        self._bm25_weight = bm25_weight
        self._dense_weight = dense_weight

    @property
    def name(self) -> str:
        return "hybrid_rrf"

    # ------------------------------------------------------------------
    # RRF Core
    # ------------------------------------------------------------------
    @staticmethod
    def _rrf_score(rank: int, k: int) -> float:
        """Compute the RRF contribution for a single document at a given rank."""
        return 1.0 / (k + rank)

    def _fuse(
        self,
        bm25_results: list[RetrievalResult],
        dense_results: list[RetrievalResult],
    ) -> dict[str, float]:
        """
        Compute fused RRF scores for all candidate documents.

        Args:
            bm25_results:  Ranked results from BM25.
            dense_results: Ranked results from Dense retriever.

        Returns:
            Mapping of ISBN-13 → fused RRF score (higher is better).
        """
        rrf_scores: dict[str, float] = defaultdict(float)

        for result in bm25_results:
            rrf_scores[result.isbn13] += (
                self._bm25_weight * self._rrf_score(result.rank, self._rrf_k)
            )

        for result in dense_results:
            rrf_scores[result.isbn13] += (
                self._dense_weight * self._rrf_score(result.rank, self._rrf_k)
            )

        return dict(rrf_scores)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------
    def search(self, query: str, top_k: int = 10) -> list[RetrievalResult]:
        """
        Retrieve top-k documents using Reciprocal Rank Fusion.

        Workflow:
        1. BM25 search(query, candidate_pool)
        2. Dense search(query, candidate_pool)
        3. RRF fusion of ranked lists
        4. Return top-k by fused score

        Args:
            query:  Natural-language search query.
            top_k:  Number of results to return after fusion.

        Returns:
            Ranked list of ``RetrievalResult`` with RRF scores.
        """
        logger.debug(
            "HybridRRF search: query='%s', top_k=%d, pool=%d, rrf_k=%d",
            query[:60],
            top_k,
            self._candidate_pool,
            self._rrf_k,
        )

        bm25_results = self._bm25.search(query, top_k=self._candidate_pool)
        dense_results = self._dense.search(query, top_k=self._candidate_pool)

        fused_scores = self._fuse(bm25_results, dense_results)

        # Sort by fused score descending
        sorted_items = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        # Build title map from sub-retriever results for output enrichment
        title_map: dict[str, str] = {}
        for r in bm25_results + dense_results:
            if r.title:
                title_map[r.isbn13] = r.title

        results: list[RetrievalResult] = []
        for rank, (isbn, score) in enumerate(sorted_items, start=1):
            results.append(
                RetrievalResult(
                    isbn13=isbn,
                    title=title_map.get(isbn, ""),
                    score=score,
                    rank=rank,
                )
            )

        return results
