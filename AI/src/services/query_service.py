"""
Query Service – batch query generation over a list of books.

Handles:
- Chunking the full book list into configurable batches
- Calling the LLM query generation chain once per batch
- Logging progress and failures per batch
- Returning a flat list of BookQueries aligned with input books
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

from src.chains.query_generation_chain import format_books_for_prompt
from src.config.settings import Settings
from src.schemas.query import BatchQueryResponse, BookInfo, BookQueries

if TYPE_CHECKING:
    from langchain_core.runnables import Runnable

logger = logging.getLogger(__name__)


class QueryService:
    """
    Orchestrates batch query generation using a LangChain chain.

    Args:
        chain:    A LangChain ``Runnable`` that outputs ``BatchQueryResponse``.
                  Build with ``build_query_generation_chain(settings)``.
        settings: Application settings (used for batch size and queries_per_book).
    """

    def __init__(self, chain: "Runnable", settings: Settings) -> None:
        self._chain = chain
        self._settings = settings

    def generate_queries_batch(self, books: list[BookInfo]) -> list[BookQueries]:
        """
        Generate queries for all books by calling the LLM in configurable batches.

        Args:
            books: List of ``BookInfo`` objects to generate queries for.

        Returns:
            Flat list of ``BookQueries`` in the same order as input.
            Books that fail (after retries) produce an empty queries list.
        """
        batch_size = self._settings.query_generation_batch_size
        queries_per_book = self._settings.queries_per_book
        all_results: list[BookQueries] = []

        chunks = [books[i: i + batch_size] for i in range(0, len(books), batch_size)]
        logger.info(
            "Generating queries for %d books in %d batches (batch_size=%d, queries_per_book=%d)",
            len(books),
            len(chunks),
            batch_size,
            queries_per_book,
        )

        for batch_idx, batch in enumerate(chunks, start=1):
            logger.info("Processing batch %d / %d (%d books)…", batch_idx, len(chunks), len(batch))
            batch_results = self._process_batch(batch, queries_per_book)
            all_results.extend(batch_results)

        logger.info(
            "Query generation complete: %d books → %d BookQueries",
            len(books),
            len(all_results),
        )
        return all_results

    def _process_batch(
        self,
        batch: list[BookInfo],
        queries_per_book: int,
    ) -> list[BookQueries]:
        """
        Call the LLM chain for a single batch of books with retry logic.

        Args:
            batch:           Subset of books for this batch call.
            queries_per_book: Target number of queries per book.

        Returns:
            List of ``BookQueries`` for this batch.
            Falls back to empty queries on persistent failure.
        """
        try:
            response = self._call_chain_with_retry(batch, queries_per_book)
            isbn_to_queries = {bq.isbn13: bq for bq in response.books}

            # Ensure output aligns with input order (LLM may reorder)
            results: list[BookQueries] = []
            for book in batch:
                if book.isbn13 in isbn_to_queries:
                    results.append(isbn_to_queries[book.isbn13])
                else:
                    logger.warning(
                        "LLM did not return queries for ISBN %s in batch – using empty list",
                        book.isbn13,
                    )
                    results.append(BookQueries(isbn13=book.isbn13, queries=[]))

            return results

        except Exception as exc:
            logger.error(
                "Batch %s failed after retries: %s. Returning empty queries for batch.",
                [b.isbn13 for b in batch],
                exc,
                exc_info=True,
            )
            return [BookQueries(isbn13=b.isbn13, queries=[]) for b in batch]

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    def _call_chain_with_retry(
        self,
        batch: list[BookInfo],
        queries_per_book: int,
    ) -> BatchQueryResponse:
        """Invoke the LLM chain with exponential-backoff retry."""
        books_text = format_books_for_prompt(batch)
        return self._chain.invoke(
            {
                "queries_per_book": queries_per_book,
                "num_books": len(batch),
                "books_text": books_text,
            }
        )
