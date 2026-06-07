"""
Relevance-judging Pydantic schemas.

Defines the data contracts for the LLM-as-judge pipeline that assigns
relevance scores to (query, book) pairs.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class RelevanceScore(BaseModel):
    """
    Structured relevance judgment for a single (query, book) pair.

    The ``reason`` field is mandatory so every judgment can be audited
    or used for fine-tuning the judge model later.
    """

    score: int = Field(
        description=(
            "Relevance score: "
            "0 = not relevant, "
            "1 = somewhat relevant, "
            "2 = highly relevant."
        ),
    )
    reason: str = Field(
        description=(
            "Concise explanation (1-3 sentences) justifying the score. "
            "Used for auditing and debugging."
        ),
    )

    @field_validator("score")
    @classmethod
    def validate_score_range(cls, v: int) -> int:
        """Ensure the score is within the valid [0, 2] range."""
        if v not in (0, 1, 2):
            raise ValueError(f"Relevance score must be 0, 1, or 2; got {v!r}")
        return v


class BookRelevance(BaseModel):
    """Relevance judgment for a specific book isbn13."""

    isbn13: str = Field(description="ISBN-13 of the judged book.")
    relevance: RelevanceScore = Field(description="The LLM's relevance judgment.")


class BatchRelevanceResponse(BaseModel):
    """
    Batch relevance judgments returned in a single LLM call.

    Allows judging multiple (query, book) pairs per API call to reduce cost.
    """

    judgments: list[BookRelevance] = Field(
        description="One BookRelevance entry per candidate book.",
    )
