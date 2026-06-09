"""
Unit tests for the query generation chain and QueryService.

Uses mocked LLM chains – no actual OpenAI API calls are made.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.schemas.query import BatchQueryResponse, BookInfo, BookQueries
from src.services.query_service import QueryService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_batch_response() -> BatchQueryResponse:
    """A valid BatchQueryResponse with queries for two books."""
    return BatchQueryResponse(
        books=[
            BookQueries(
                isbn13="9780000000001",
                queries=[
                    "alien invasion sci-fi",
                    "humanity fighting alien threat strategy",
                    "science fiction novel about secret plans to deceive extraterrestrial invaders",
                ],
            ),
            BookQueries(
                isbn13="9780000000002",
                queries=[
                    "fantasy wizard coming of age",
                    "legendary musician magic school",
                    "epic fantasy tale of a gifted young man who becomes a legend",
                ],
            ),
        ]
    )


@pytest.fixture
def mock_chain(mock_batch_response: BatchQueryResponse) -> MagicMock:
    """A mock LangChain Runnable that always returns the preset BatchQueryResponse."""
    chain = MagicMock()
    chain.invoke.return_value = mock_batch_response
    return chain


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestQueryService:
    def test_generate_queries_returns_correct_count(
        self,
        mock_chain: MagicMock,
        mock_settings,
        sample_books: list[BookInfo],
    ):
        service = QueryService(chain=mock_chain, settings=mock_settings)
        results = service.generate_queries_batch(sample_books[:2])
        assert len(results) == 2

    def test_isbn_alignment(
        self,
        mock_chain: MagicMock,
        mock_settings,
        sample_books: list[BookInfo],
    ):
        """Output ISBNs must match input ISBNs in the same order."""
        service = QueryService(chain=mock_chain, settings=mock_settings)
        results = service.generate_queries_batch(sample_books[:2])
        assert results[0].isbn13 == sample_books[0].isbn13
        assert results[1].isbn13 == sample_books[1].isbn13

    def test_queries_are_populated(
        self,
        mock_chain: MagicMock,
        mock_settings,
        sample_books: list[BookInfo],
    ):
        service = QueryService(chain=mock_chain, settings=mock_settings)
        results = service.generate_queries_batch(sample_books[:2])
        for bq in results:
            assert len(bq.queries) > 0

    def test_batching_splits_correctly(
        self,
        mock_batch_response: BatchQueryResponse,
        mock_settings,
        sample_books: list[BookInfo],
    ):
        """With batch_size=1, the chain should be called once per book."""
        mock_settings_small = mock_settings
        mock_settings_small.query_generation_batch_size = 1

        # Chain returns single-book responses
        single_response = BatchQueryResponse(
            books=[BookQueries(isbn13=sample_books[0].isbn13, queries=["q1", "q2"])]
        )
        chain = MagicMock()
        chain.invoke.return_value = single_response

        service = QueryService(chain=chain, settings=mock_settings_small)

        # Patch to return different ISBN per call
        responses = [
            BatchQueryResponse(books=[BookQueries(isbn13=b.isbn13, queries=["q1"])]) for b in sample_books[:3]
        ]
        chain.invoke.side_effect = responses

        results = service.generate_queries_batch(sample_books[:3])
        assert chain.invoke.call_count == 3
        assert len(results) == 3

    def test_missing_isbn_in_response_returns_empty(
        self,
        mock_settings,
        sample_books: list[BookInfo],
    ):
        """If LLM omits a book from the response, an empty BookQueries is returned."""
        incomplete_response = BatchQueryResponse(
            books=[BookQueries(isbn13="9780000000001", queries=["query one"])]
            # 9780000000002 is missing
        )
        chain = MagicMock()
        chain.invoke.return_value = incomplete_response

        service = QueryService(chain=chain, settings=mock_settings)
        results = service.generate_queries_batch(sample_books[:2])

        assert len(results) == 2
        assert results[1].isbn13 == sample_books[1].isbn13
        assert results[1].queries == []

    def test_chain_failure_returns_empty_queries(
        self,
        mock_settings,
        sample_books: list[BookInfo],
    ):
        """If the chain raises an exception, empty BookQueries are returned for the batch."""
        chain = MagicMock()
        chain.invoke.side_effect = RuntimeError("API error")

        service = QueryService(chain=chain, settings=mock_settings)
        results = service.generate_queries_batch(sample_books[:2])

        assert len(results) == 2
        for bq in results:
            assert bq.queries == []


class TestFormatBooksForPrompt:
    def test_output_contains_isbn(self, sample_books: list[BookInfo]):
        from src.chains.query_generation_chain import format_books_for_prompt
        text = format_books_for_prompt(sample_books[:1])
        assert sample_books[0].isbn13 in text

    def test_output_contains_title(self, sample_books: list[BookInfo]):
        from src.chains.query_generation_chain import format_books_for_prompt
        text = format_books_for_prompt(sample_books[:1])
        assert sample_books[0].title in text

    def test_description_truncated(self, sample_books: list[BookInfo]):
        from src.chains.query_generation_chain import format_books_for_prompt
        long_book = BookInfo(
            isbn13="9780000099999",
            title="Test Book",
            description="x" * 2000,
        )
        text = format_books_for_prompt([long_book])
        # Description is truncated to 600 chars in the formatter
        assert "x" * 601 not in text
