"""
Query-related Pydantic schemas.

Defines the data contracts for:
- Input book information fed to the LLM
- Structured query output from the LLM (single book and batch)
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class BookInfo(BaseModel):
    """Minimal representation of a book used as LLM input for query generation."""

    isbn13: str = Field(description="Unique book identifier (ISBN-13).")
    title: str = Field(description="Book title.")
    description: str = Field(description="Book description / synopsis.")
    categories: str = Field(
        default="",
        description="Comma-separated category / genre tags.",
    )


class BookQueries(BaseModel):
    """
    Structured output for queries generated for a single book.

    The LLM is asked to produce queries of varying lengths to simulate
    different user search behaviours.
    """

    isbn13: str = Field(
        description="ISBN-13 of the source book these queries were generated for.",
    )
    queries: list[str] = Field(
        description=(
            "List of search queries relevant to the book. "
            "Should include short (1-3 words), medium (4-8 words), "
            "and long (9+ words) queries."
        ),
    )


class BatchQueryResponse(BaseModel):
    """
    Structured output returned by the LLM for a batch of books.

    Wrapping in a single batch call reduces API round-trips and token overhead.
    """

    books: list[BookQueries] = Field(
        description="One BookQueries entry per book in the input batch.",
    )
