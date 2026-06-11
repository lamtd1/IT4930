"""
Candidate Service – multi-retriever candidate pool for ground-truth generation.

Retrieves candidates from ALL five retrievers in parallel, then unions the
results (deduplicated by ISBN-13) before passing them to the LLM judge.

Workflow:
    Query
      ↓
    ┌─────────────────────────────────────────────────────────┐
    │  [Concurrent – 5 threads]                               │
    │  TF-IDF   → top-N  ┐                                   │
    │  BM25     → top-N  ├─ union (dedup, order-preserved)   │
    │  Dense    → top-N  │                                    │
    │  Hybrid   → top-N  │                                    │
    │  Rerank   → top-N  ┘                                    │
    └─────────────────────────────────────────────────────────┘
      ↓
    Combined candidate pool (unique ISBNs)
      ↓
    LLM Relevance Judging (JudgeService)
      ↓
    Relevant ISBNs

Pool size per retriever is controlled by ``ground_truth_candidate_pool``
in settings (env: GROUND_TRUTH_CANDIDATE_POOL).
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.config.settings import Settings
from src.retrieval.base import BaseRetriever
from src.schemas.retrieval import RetrievalResult

logger = logging.getLogger(__name__)


class CandidateService:
    """
    Retrieves candidates for ground-truth generation from ALL retrievers.

    Each retriever is queried concurrently with the same ``pool_size``.
    Results are unioned (deduplicated by ISBN-13, insertion-order preserved)
    to form a comprehensive candidate set for LLM relevance judging.

    Args:
        retrievers: Mapping of retriever name → ``BaseRetriever`` instance.
                    Typically all five: tfidf, bm25, dense, hybrid_rrf, rerank.
        settings:   Application settings (``ground_truth_candidate_pool``).
    """

    def __init__(
        self,
        retrievers: dict[str, BaseRetriever],
        settings: Settings,
    ) -> None:
        self._retrievers = retrievers
        self._settings = settings

    def get_candidates(
        self,
        query: str,
        pool_size: int | None = None,
    ) -> list[RetrievalResult]:
        """
        Retrieve candidate books from all retrievers and return a deduplicated union.

        Each retriever is called concurrently in its own thread.  Results from
        all retrievers are merged in the order: tfidf → bm25 → dense →
        hybrid_rrf → rerank, deduplicated by ISBN-13 (first occurrence wins).

        Args:
            query:     Natural-language search query.
            pool_size: Override for ``settings.ground_truth_candidate_pool``.
                       Uses settings value if ``None``.

        Returns:
            Deduplicated list of ``RetrievalResult`` objects drawn from the
            union of all retriever results.
        """
        n = pool_size if pool_size is not None else self._settings.ground_truth_candidate_pool

        logger.debug(
            "Retrieving %d candidates per retriever (%d retrievers) for GT query: '%s'",
            n,
            len(self._retrievers),
            query[:60],
        )

        # Run all retrievers concurrently
        retriever_results: dict[str, list[RetrievalResult]] = {}

        def _search(name: str, retriever: BaseRetriever) -> tuple[str, list[RetrievalResult]]:
            try:
                return name, retriever.search(query, top_k=n)
            except Exception as exc:
                logger.error("Retriever '%s' failed during GT candidate fetch: %s", name, exc)
                return name, []

        with ThreadPoolExecutor(max_workers=len(self._retrievers)) as pool:
            futures = {
                pool.submit(_search, name, r): name
                for name, r in self._retrievers.items()
            }
            for future in as_completed(futures):
                name, results = future.result()
                retriever_results[name] = results

        # Union: merge in a stable order, dedup by ISBN-13 (first seen wins)
        seen_isbns: set[str] = set()
        combined: list[RetrievalResult] = []

        # Stable merge order: respect the insertion order of self._retrievers
        for name in self._retrievers:
            for result in retriever_results.get(name, []):
                if result.isbn13 not in seen_isbns:
                    seen_isbns.add(result.isbn13)
                    combined.append(result)

        logger.debug(
            "Combined candidate pool: %d unique ISBNs from %d retrievers "
            "(per-retriever pool=%d)",
            len(combined),
            len(self._retrievers),
            n,
        )

        # Log per-retriever counts at DEBUG level
        for name in self._retrievers:
            cnt = len(retriever_results.get(name, []))
            logger.debug("  %-12s → %d candidates", name, cnt)

        return combined
