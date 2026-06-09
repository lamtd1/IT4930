"""
Retrieval result Pydantic schemas.

Defines the standard output contract for all retrievers so results can be
processed uniformly by the evaluation and hybrid fusion layers.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class RetrievalResult(BaseModel):
    """
    A single document returned by a retriever for a given query.

    All retrievers must return ``list[RetrievalResult]`` so downstream
    components (evaluator, hybrid fusion) are retriever-agnostic.
    """

    isbn13: str = Field(description="Unique book identifier (ISBN-13).")
    title: str = Field(default="", description="Book title (may be empty for lightweight results).")
    score: float = Field(
        description=(
            "Retrieval relevance score. "
            "Semantics vary by retriever (cosine similarity, BM25 score, etc.)."
        ),
    )
    rank: int = Field(
        default=0,
        description="1-based rank within the result list (set by the retriever).",
    )


class RetrievalResultList(BaseModel):
    """Wrapper for a ranked list of retrieval results."""

    query: str = Field(description="The query that produced these results.")
    results: list[RetrievalResult] = Field(
        description="Ranked list of retrieval results (most relevant first).",
    )

    def isbn_list(self) -> list[str]:
        """Return an ordered list of ISBN-13 identifiers (most relevant first)."""
        return [r.isbn13 for r in self.results]
