"""
Judge Service – LLM-as-judge relevance scoring for (query, book) pairs.

Handles:
- Calling the relevance judge chain per (query, book) pair
- In-memory caching to avoid re-judging identical pairs
- Retry with exponential backoff on API errors
- Detailed logging for every judgment (for auditing)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config.settings import Settings
from src.schemas.relevance import RelevanceScore

if TYPE_CHECKING:
    from langchain_core.runnables import Runnable

logger = logging.getLogger(__name__)


class JudgeService:
    """
    Orchestrates LLM relevance judging for (query, book) pairs.

    Results are cached in-memory so the same pair is never judged twice
    within a single pipeline run.

    Args:
        chain:    A LangChain ``Runnable`` that outputs ``RelevanceScore``.
                  Build with ``build_relevance_judge_chain(settings)``.
        settings: Application settings (relevance_threshold, model info).
    """

    def __init__(self, chain: "Runnable", settings: Settings) -> None:
        self._chain = chain
        self._settings = settings
        self._cache: dict[tuple[str, str], RelevanceScore] = {}

    @property
    def cache_size(self) -> int:
        """Number of cached judgments."""
        return len(self._cache)

    def judge_relevance(
        self,
        query: str,
        isbn13: str,
        book_title: str,
        book_description: str,
        use_cache: bool = True,
    ) -> RelevanceScore:
        """
        Judge the relevance of a book for a given query.

        Args:
            query:            Natural-language search query.
            isbn13:           ISBN-13 of the candidate book (used as cache key).
            book_title:       Book title.
            book_description: Book description (truncated to ~400 tokens internally).
            use_cache:        If True, return cached result for identical (query, isbn13) pairs.

        Returns:
            ``RelevanceScore`` with score (0/1/2) and reason.
        """
        cache_key = (query, isbn13)

        if use_cache and cache_key in self._cache:
            logger.debug("Cache hit for ISBN %s, query='%s'", isbn13, query[:50])
            return self._cache[cache_key]

        result = self._judge_with_retry(query, book_title, book_description)

        logger.info(
            "Relevance judgment: ISBN=%s | score=%d | query='%s' | reason='%s'",
            isbn13,
            result.score,
            query[:60],
            result.reason[:80],
        )

        if use_cache:
            self._cache[cache_key] = result

        return result

    def is_relevant(self, score: RelevanceScore) -> bool:
        """
        Check whether a relevance score meets the configured threshold.

        Args:
            score: ``RelevanceScore`` returned by ``judge_relevance``.

        Returns:
            ``True`` if ``score.score >= settings.relevance_threshold``.
        """
        return score.score >= self._settings.relevance_threshold

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=4, max=120),
        reraise=True,
    )
    def _judge_with_retry(
        self,
        query: str,
        book_title: str,
        book_description: str,
    ) -> RelevanceScore:
        """Invoke the relevance judge chain with retry on transient errors.

        Uses exponential backoff (4s → 8s → 16s → … → 120s) to handle
        OpenAI rate limits (429) without wasting retries on quick failures.
        """
        # Truncate description to ~2000 chars to stay within token budget
        truncated_desc = book_description[:2000]
        return self._chain.invoke(
            {
                "query": query,
                "book_title": book_title,
                "book_description": truncated_desc,
            }
        )
