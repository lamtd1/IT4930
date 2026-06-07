"""
Reranking Retriever: Dense retrieval followed by Cross-Encoder reranking.

Workflow:
    Query
      ↓
    Dense Retrieval (candidate_pool candidates)
      ↓
    Cross-Encoder scoring of (query, description) pairs
      ↓
    Reranked final results (top_k)

The cross-encoder reads the full query and full document text jointly
so it captures fine-grained relevance signals invisible to bi-encoders.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.retrieval.base import BaseRetriever
from src.schemas.retrieval import RetrievalResult

if TYPE_CHECKING:
    from src.retrieval.dense_retriever import DenseRetriever

logger = logging.getLogger(__name__)


class RerankRetriever(BaseRetriever):
    """
    Two-stage retriever: Dense bi-encoder → Cross-Encoder reranking.

    Args:
        dense_retriever:  Initialised DenseRetriever for first-stage recall.
        rerank_model:     CrossEncoder model name or path
                          (e.g. ``"BAAI/bge-reranker-base"``).
        candidate_pool:   Number of dense candidates passed to the cross-encoder.
                          Must be ≥ ``top_k``.
    """

    def __init__(
        self,
        dense_retriever: DenseRetriever,
        rerank_model: str,
        candidate_pool: int = 20,
    ) -> None:
        self._dense = dense_retriever
        self._rerank_model_name = rerank_model
        self._candidate_pool = candidate_pool
        self._cross_encoder = None

    @property
    def name(self) -> str:
        return "rerank"

    def _get_cross_encoder(self):
        """Lazy-load the CrossEncoder model."""
        if self._cross_encoder is None:
            from sentence_transformers import CrossEncoder  # noqa: PLC0415
            logger.info("Loading CrossEncoder: %s", self._rerank_model_name)
            self._cross_encoder = CrossEncoder(self._rerank_model_name, max_length=512)
        return self._cross_encoder

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------
    def search(self, query: str, top_k: int = 10) -> list[RetrievalResult]:
        """
        Retrieve and rerank top-k documents.

        Step 1: Dense retrieval fetches ``candidate_pool`` candidates.
        Step 2: CrossEncoder scores every (query, description) pair.
        Step 3: Candidates are re-sorted by cross-encoder score; top-k returned.

        Args:
            query:  Natural-language search query.
            top_k:  Number of final results after reranking.

        Returns:
            Ranked list of ``RetrievalResult`` with cross-encoder scores.
        """
        # Ensure candidate_pool >= top_k to avoid returning fewer than expected
        pool_size = max(self._candidate_pool, top_k)

        logger.debug(
            "Rerank search: query='%s', pool=%d, top_k=%d, model=%s",
            query[:60],
            pool_size,
            top_k,
            self._rerank_model_name,
        )

        # Stage 1: Dense recall
        dense_results = self._dense.search(query, top_k=pool_size)

        if not dense_results:
            logger.warning("Dense retriever returned no results for query: %s", query)
            return []

        # Stage 2: Fetch descriptions from ChromaDB for scoring
        # DenseRetriever's collection holds documents (descriptions)
        collection = self._dense._get_collection()  # type: ignore[attr-defined]
        isbn_list = [r.isbn13 for r in dense_results]

        raw = collection.get(ids=isbn_list, include=["documents", "metadatas"])

        # Map isbn → description for pair construction
        isbn_to_desc: dict[str, str] = {}
        isbn_to_title: dict[str, str] = {}
        for isbn, doc, meta in zip(raw["ids"], raw["documents"], raw["metadatas"]):
            isbn_to_desc[isbn] = doc or ""
            isbn_to_title[isbn] = meta.get("title", "") if meta else ""

        # Stage 3: Cross-encoder scoring
        cross_encoder = self._get_cross_encoder()
        pairs = [(query, isbn_to_desc.get(r.isbn13, "")) for r in dense_results]
        ce_scores = cross_encoder.predict(pairs, show_progress_bar=False)

        # Attach cross-encoder scores and re-sort
        scored: list[tuple[RetrievalResult, float]] = list(zip(dense_results, ce_scores))
        scored.sort(key=lambda x: x[1], reverse=True)

        results: list[RetrievalResult] = []
        for rank, (result, score) in enumerate(scored[:top_k], start=1):
            results.append(
                RetrievalResult(
                    isbn13=result.isbn13,
                    title=isbn_to_title.get(result.isbn13, result.title),
                    score=float(score),
                    rank=rank,
                )
            )

        return results
