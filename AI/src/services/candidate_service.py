"""
Candidate Service – dense retrieval of ground-truth candidate books.

This service is EXCLUSIVELY used for ground-truth generation.
It is deliberately separate from the HybridRRFRetriever so ground truth
is never biased by the hybrid fusion strategy being evaluated.

Workflow:
    Query
      ↓
    Dense Retrieval (ground_truth_candidate_pool candidates)
      ↓
    LLM Relevance Judging (JudgeService)
      ↓
    Relevant ISBNs
"""

from __future__ import annotations

import logging

from src.config.settings import Settings
from src.retrieval import DenseRetriever
from src.schemas.retrieval import RetrievalResult

logger = logging.getLogger(__name__)


class CandidateService:
    """
    Retrieves dense candidates for ground-truth generation.

    Uses only the dense retriever (bi-encoder) for candidate generation.
    This is an intentional design choice: the candidate pool must not depend
    on any evaluated retriever to avoid circularity in the benchmark.

    Args:
        dense_retriever: Initialised ``DenseRetriever`` for candidate retrieval.
        settings:        Application settings (ground_truth_candidate_pool).
    """

    def __init__(
        self,
        dense_retriever: DenseRetriever,
        settings: Settings,
    ) -> None:
        self._dense = dense_retriever
        self._settings = settings

    def get_candidates(
        self,
        query: str,
        pool_size: int | None = None,
    ) -> list[RetrievalResult]:
        """
        Retrieve candidate books for relevance judging.

        Args:
            query:     Natural-language search query.
            pool_size: Override for ``settings.ground_truth_candidate_pool``.
                       Uses settings value if ``None``.

        Returns:
            Ranked list of ``RetrievalResult`` objects (dense-ranked candidates).
        """
        n = pool_size if pool_size is not None else self._settings.ground_truth_candidate_pool

        logger.debug(
            "Retrieving %d dense candidates for GT query: '%s'",
            n,
            query[:60],
        )

        candidates = self._dense.search(query, top_k=n)

        logger.debug(
            "Retrieved %d candidates (requested %d)",
            len(candidates),
            n,
        )

        return candidates
